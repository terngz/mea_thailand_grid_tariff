"""Data coordinator ที่ดึงและ cache ข้อมูลอัตราค่าไฟ MEA."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from pathlib import Path

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DEFAULT_SCAN_INTERVAL_DAYS,
    DOMAIN,
    FALLBACK_FT,
    FT_URLS,
    TARIFF_PAGES,
)
from .parser import parse_ft, parse_tariff_page, RateBlock, Tier

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "th,en-US;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

# จำนวนครั้งที่ลองใหม่เมื่อ connection ถูก reset/ต่อไม่ติด
# (ยืนยันแล้วว่าเว็บ+เน็ตปกติดี — เจอ reset ช่วงที่ทดสอบถี่ๆ น่าจะเป็นการบล็อกชั่วคราวของ
# ระบบป้องกัน bot ฝั่งเว็บ เช่น F5 BIG-IP ASM ที่สังเกตเจอจาก cookie "TSxxxxxxxx")
FETCH_RETRIES = 3
FETCH_RETRY_DELAY = 3  # วินาที, เพิ่มแบบ exponential


def _get_fallback_blocks(tariff_key: str) -> list[RateBlock]:
    """คืนค่า Mock Blocks ที่ถูกต้องตามประเภท Tariff เพื่อให้ Sensor Entities ถูกสร้างครบเสมอ."""
    key = str(tariff_key).lower()
    
    if "1.1" in key or "le150" in key:
        return [
            RateBlock(
                key="le150",
                title="1.1 บ้านอยู่อาศัย (ไม่เกิน 150 หน่วย)",
                tiers=[
                    Tier(label="15 หน่วยแรก", start=1, end=15, rate=2.3488),
                    Tier(label="16 - 25 หน่วย", start=16, end=25, rate=2.9882),
                    Tier(label="26 - 200 หน่วย", start=26, end=200, rate=3.2405),
                    Tier(label="201 - 400 หน่วย", start=201, end=400, rate=4.2218),
                    Tier(label="401 หน่วยเป็นต้นไป", start=401, end=None, rate=4.4217),
                ],
                service_charge=8.19,
            )
        ]
    
    if "1.3" in key or "tou" in key:
        is_131 = "1.3.1" in key or "131" in key
        b_key = "tou_131" if is_131 else "tou_132"
        return [
            RateBlock(
                key=b_key,
                title="1.3 TOU บ้านอยู่อาศัย",
                on_peak=5.1135 if is_131 else 5.7982,
                off_peak=2.6037 if is_131 else 2.6369,
                service_charge=312.24 if is_131 else 24.62,
            )
        ]

    # Default / Fallback สำหรับ 1.2 (gt150)
    return [
        RateBlock(
            key="gt150",
            title="1.2 บ้านอยู่อาศัย (เกิน 150 หน่วย)",
            tiers=[
                Tier(label="1 - 200 หน่วย", start=1, end=200, rate=3.2484),
                Tier(label="201 - 400 หน่วย", start=201, end=400, rate=4.2218),
                Tier(label="401 หน่วยเป็นต้นไป", start=401, end=None, rate=4.4217),
            ],
            service_charge=24.62,
        )
    ]


class MeaTariffCoordinator(DataUpdateCoordinator):
    """ดึงข้อมูลจากเว็บ MEA ทุก 12 ชั่วโมง."""

    def __init__(
        self,
        hass: HomeAssistant,
        tariff_key: str,
        sub_tariff_key: str,
        entry_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{sub_tariff_key}",
            update_interval=timedelta(days=DEFAULT_SCAN_INTERVAL_DAYS),
        )
        self.tariff_key = tariff_key
        self.sub_tariff_key = sub_tariff_key
        self.session = async_get_clientsession(hass)
        self._store = Store(hass, 1, f"{DOMAIN}_{entry_id}_cache")

    async def _fetch(self, url: str) -> str:
        last_err: Exception | None = None
        for attempt in range(1, FETCH_RETRIES + 1):
            try:
                async with self.session.get(
                    url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    _LOGGER.debug(
                        "GET %s -> status=%s content-type=%s content-length=%s (ครั้งที่ %d)",
                        url,
                        resp.status,
                        resp.headers.get("Content-Type"),
                        resp.headers.get("Content-Length"),
                        attempt,
                    )
                    resp.raise_for_status()
                    text = await resp.text()
                    _LOGGER.debug("ได้ HTML จาก %s ยาว %d ตัวอักษร", url, len(text))
                    return text
            except (
                aiohttp.ClientConnectorError,
                aiohttp.ServerDisconnectedError,
                aiohttp.ClientOSError,
            ) as err:
                # มักเป็นการบล็อกแบบสุ่มของ WAF/anti-bot (connection reset ระหว่าง handshake)
                # ลองใหม่ก่อนค่อยยอมแพ้ เพราะบ่อยครั้งรอบถัดไปจะผ่าน
                last_err = err
                _LOGGER.debug(
                    "เชื่อมต่อ %s ไม่สำเร็จ (ครั้งที่ %d/%d): %s",
                    url,
                    attempt,
                    FETCH_RETRIES,
                    err,
                )
                if attempt < FETCH_RETRIES:
                    await asyncio.sleep(FETCH_RETRY_DELAY * attempt)
        raise last_err

    async def _dump_debug_html(self, html: str) -> None:
        """เขียน HTML ที่ดึงได้ล่าสุดลงไฟล์ เพื่อเปิดดูตรวจสอบว่าเว็บส่งอะไรกลับมาจริง."""
        path = self.hass.config.path(f"mea_debug_{self.sub_tariff_key}.html")
        try:
            await self.hass.async_add_executor_job(
                lambda: Path(path).write_text(html, encoding="utf-8")
            )
            _LOGGER.debug("บันทึก HTML debug ไว้ที่ %s", path)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("เขียนไฟล์ debug ไม่สำเร็จ: %s", err)

    async def _get_ft(self) -> float | None:
        for url in FT_URLS:
            try:
                html = await self._fetch(url)
                ft = await self.hass.async_add_executor_job(parse_ft, html)
                if ft is not None:
                    _LOGGER.debug("Ft = %s บาท/หน่วย จาก %s", ft, url)
                    return ft
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("ดึง Ft จาก %s ไม่สำเร็จ: %s", url, err)
        return None

    async def _async_update_data(self) -> dict:
        page = TARIFF_PAGES.get(self.tariff_key, TARIFF_PAGES[next(iter(TARIFF_PAGES))])
        blocks = []
        try:
            html = await self._fetch(page["url"])
            await self._dump_debug_html(html)
            blocks = await self.hass.async_add_executor_job(parse_tariff_page, html)
            _LOGGER.debug(
                "parse_tariff_page ได้ %d block(s): %s",
                len(blocks),
                [b.key for b in blocks],
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("ดึงหน้า MEA ไม่สำเร็จ: %s", err)

        if not blocks:
            if self.data and self.data.get("blocks"):
                _LOGGER.warning("Parse ไม่สำเร็จ แต่จะใช้ข้อมูลเดิมที่มีอยู่")
                return {**self.data, "healthy": False}
            
            _LOGGER.warning(
                "Parse ไม่สำเร็จ ใช้ข้อมูลจำลองตาม Tariff Key: %s", self.sub_tariff_key
            )
            blocks = _get_fallback_blocks(self.sub_tariff_key)

        ft = await self._get_ft()
        if ft is None:
            ft = FALLBACK_FT
            _LOGGER.warning("parse ค่า Ft ไม่ได้ ใช้ค่าสำรอง %s", FALLBACK_FT)

        data = {
            "name": page["name"],
            "url": page["url"],
            "blocks": blocks,
            "ft": ft,
            "healthy": True,
        }
        await self._store.async_save({"ft": ft, "blocks": len(blocks)})
        return data