"""ค่าคงที่ของ MEA Thailand Grid Tariffs."""
from __future__ import annotations

import json
import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mea_thailand_grid_tariffs"
INTEGRATION_NAME = "MEA Thailand Grid Tariffs"
DEFAULT_SCAN_INTERVAL_DAYS = 90

BASE = "https://www.mea.or.th"

TARIFF_PAGES: dict[str, dict[str, str]] = {
    "residential": {
        "name": "บ้านอยู่อาศัย (ประเภท 1)",
        "url": f"{BASE}/our-services/service-rates/other/D5xEaEwgU",
    },
}

FT_URLS: list[str] = [
    f"{BASE}/our-services/service-rates/ft/statistics",
    f"{BASE}/our-services/tariff-calculation/latestft",
    f"{BASE}/our-services/service-rates/latestft/acj9pdObH",
]

FALLBACK_FT = 0.1623

CONF_TARIFF = "tariff"
CONF_SUB_TARIFF = "sub_tariff"

SERVICE_REFRESH = "refresh"

# --- Entity / Device naming ---------------------------------------------
# ฐานของ entity_id ทุกตัวในระบบ (บ้านอยู่อาศัย ประเภท 1 เท่านั้นตอนนี้ จึง fix เป็น residential_1)
ENTITY_ID_BASE = "mea_thailand_grid_tariff"

SUB_TARIFF_ID_SLUGS: dict[str, str] = {
    "le150": "type_1_1_below_150",
    "gt150": "type_1_2_greater_150",
    "tou_131": "type_1_3_1_tou_12_24",
    "tou_132": "type_1_3_2_tou_under_12",
}

# ชื่อ Config Entry (หัวข้อบนสุดใน Services) — คงที่ ไม่ผันตาม sub_tariff
RESIDENTIAL_TITLE_TH = "MEA บ้านอยู่อาศัย (ประเภท 1)"
RESIDENTIAL_TITLE_EN = "MEA Residential (Type 1)"


def _load_sub_tariff_labels(json_filename: str) -> dict[str, str]:
    """อ่าน label ของ sub_tariff ตรงจากไฟล์ translation (en.json/th.json) ในโฟลเดอร์เดียวกัน
    เพื่อไม่ต้อง maintain ข้อความซ้ำสองที่ — เพิ่ม/แก้ sub_tariff ใหม่แก้ที่ en.json/th.json
    ที่เดียวพอ ไม่ต้องมาแก้ const.py คู่กันอีก."""
    path = Path(__file__).parent / "translations" / json_filename
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data["selector"]["sub_tariff"]["options"]
    except (OSError, KeyError, json.JSONDecodeError) as err:
        _LOGGER.warning("อ่าน label sub_tariff จาก %s ไม่สำเร็จ: %s", json_filename, err)
        return {}


SUB_TARIFF_LABELS_EN: dict[str, str] = _load_sub_tariff_labels("en.json")
SUB_TARIFF_LABELS_TH: dict[str, str] = _load_sub_tariff_labels("th.json")


def _is_thai(language: str | None) -> bool:
    return bool(language) and str(language).strip().lower().startswith("th")


def sub_tariff_id_slug(key: str) -> str:
    """slug ภาษาอังกฤษล้วน ใช้สร้าง entity_id ให้อ่านออก (ไม่ผ่าน HA auto-slugify ภาษาไทย)."""
    return SUB_TARIFF_ID_SLUGS.get(str(key).strip().lower(), str(key).strip().lower())


def sub_tariff_label(key: str, language: str | None = None) -> str:
    """ชื่อ sub_tariff สำหรับแสดงผล (ชื่อ Device) เลือกไทย/อังกฤษตามภาษาของระบบ HA
    — ดึงจาก en.json/th.json โดยตรง (SUB_TARIFF_LABELS_EN/TH ด้านบน)."""
    k = str(key).strip().lower()
    table = SUB_TARIFF_LABELS_TH if _is_thai(language) else SUB_TARIFF_LABELS_EN
    return table.get(k, SUB_TARIFF_LABELS_EN.get(k, k))


def residential_title(language: str | None = None) -> str:
    """ชื่อ Config Entry (หัวข้อบนสุดใน Services) ตามภาษาของระบบ HA."""
    return RESIDENTIAL_TITLE_TH if _is_thai(language) else RESIDENTIAL_TITLE_EN