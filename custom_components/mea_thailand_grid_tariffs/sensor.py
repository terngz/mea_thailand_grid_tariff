"""Sensor platform สำหรับ MEA Thailand Grid Tariffs."""
from __future__ import annotations

from datetime import time
import logging
import os

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import (
    CONF_SUB_TARIFF,
    DOMAIN,
    ENTITY_ID_BASE,
    INTEGRATION_NAME,
    sub_tariff_id_slug,
    sub_tariff_label,
)
from .coordinator import MeaTariffCoordinator

_LOGGER = logging.getLogger(__name__)
CURRENCY = "THB"


def load_holidays(folder_path: str) -> set[str]:
    """โหลดรายการวันหยุดจากไฟล์ holidays.txt (YYYY-MM-DD)."""
    file_path = os.path.join(folder_path, "holidays.txt")
    holidays = set()
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        holidays.add(line)
        except Exception as err:
            _LOGGER.error("ไม่สามารถอ่านไฟล์ holidays.txt ได้: %s", err)
    return holidays


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    """ตั้งค่า Sensor Entities จาก Config Entry."""
    coordinator: MeaTariffCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    target_sub = str(entry.data.get(CONF_SUB_TARIFF, "gt150")).strip().lower()
    integration_folder = os.path.dirname(__file__)

    if coordinator.data and "blocks" in coordinator.data:
        for block in coordinator.data["blocks"]:
            b_key = str(getattr(block, "key", "")).strip().lower()

            match = False
            if not target_sub:
                match = True
            elif ("gt150" in target_sub or "1.2" in target_sub) and "gt150" in b_key:
                match = True
            elif ("le150" in target_sub or "1.1" in target_sub) and "le150" in b_key:
                match = True
            elif ("131" in target_sub or "tou_131" in target_sub) and ("131" in b_key or "tou_131" in b_key):
                match = True
            elif ("132" in target_sub or "tou_132" in target_sub) and ("132" in b_key or "tou_132" in b_key):
                match = True
            elif target_sub in b_key or b_key in target_sub:
                match = True

            if not match:
                continue

            # 1. ตารางแบบ Tier (1.1 / 1.2)
            tiers = getattr(block, "tiers", [])
            for idx in range(1, len(tiers) + 1):
                entities.append(MeaRateSensor(coordinator, entry, block.key, idx))

            # 2. ตารางแบบ TOU (1.3.1 / 1.3.2)
            if getattr(block, "on_peak", None) is not None:
                entities.append(MeaTouRateSensor(coordinator, entry, block.key, "on_peak"))
            if getattr(block, "off_peak", None) is not None:
                entities.append(MeaTouRateSensor(coordinator, entry, block.key, "off_peak"))

            # เพิ่มเฉพาะ Sensor บอกสถานะช่วงเวลา TOU เมื่อเลือกอัตรา 1.3.x
            if "131" in target_sub or "132" in target_sub or "tou" in b_key:
                entities.append(MeaTouStatusSensor(coordinator, entry, block.key, integration_folder))

            # 3. ค่าบริการ
            if getattr(block, "service_charge", None) is not None:
                entities.append(MeaServiceChargeSensor(coordinator, entry, block.key))

    # 4. ค่า Ft Rate
    entities.append(MeaFtSensor(coordinator, entry))

    add_entities(entities)


class MeaBase(CoordinatorEntity[MeaTariffCoordinator], SensorEntity):
    """Base class สำหรับ MEA Tariff Sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MeaTariffCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry

        # เก็บ slug ของ sub_tariff ไว้ใช้ซ้ำ (ใช้สร้าง object_id / device name ให้ตรงกันทุกจุด)
        self._sub_tariff = str(entry.data.get(CONF_SUB_TARIFF, "")).strip().lower()
        self._id_slug = sub_tariff_id_slug(self._sub_tariff)

        # ชื่อ Device: เลือกไทย/อังกฤษตามภาษาที่ตั้งไว้ใน Home Assistant
        language = getattr(coordinator.hass.config, "language", None)
        device_name = f"MEA {sub_tariff_label(self._sub_tariff, language)}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="@terngz (Community Integration)",
            model=f"{INTEGRATION_NAME} — Unofficial Web Scraper Sensor for MEA Tariffs",
            name=device_name,
            configuration_url="https://github.com/terngz/mea-thailand_grid_tariffs",
        )

    def _block(self, key: str):
        if not self.coordinator.data or "blocks" not in self.coordinator.data:
            return None
        for b in self.coordinator.data["blocks"]:
            if getattr(b, "key", None) == key:
                return b
        return None


class MeaRateSensor(MeaBase):
    """อัตราค่าพลังงานรายขั้น (บาท/kWh) สำหรับประเภท 1.1 / 1.2."""

    _attr_native_unit_of_measurement = f"{CURRENCY}/kWh"
    _attr_icon = "mdi:cash-multiple"
    _attr_suggested_display_precision = 4

    def __init__(self, coordinator: MeaTariffCoordinator, entry: ConfigEntry, block_key: str, index: int) -> None:
        super().__init__(coordinator, entry)
        self._key, self._index = block_key, index
        self._attr_unique_id = f"{entry.entry_id}_{block_key}_tier{index}"

        sub_code = "1_1" if "le150" in block_key else ("1_2" if "gt150" in block_key else block_key)
        self._sub_code_label = "1.1" if sub_code == "1_1" else ("1.2" if sub_code == "1_2" else sub_code)

        b = self._block(block_key)
        range_str = f"tier{index}"
        if b and hasattr(b, "tiers") and len(b.tiers) >= index:
            t = b.tiers[index - 1]
            if getattr(t, "start", None) is not None:
                end_label = f"{int(t.end)}" if getattr(t, "end", None) is not None else "onward"
                range_str = f"tier{index}_{int(t.start)}_{end_label}"

        self.entity_id = f"sensor.{ENTITY_ID_BASE}_{self._id_slug}_{range_str}"

    @property
    def name(self) -> str | None:
        b = self._block(self._key)
        if b and hasattr(b, "tiers") and len(b.tiers) >= self._index:
            t = b.tiers[self._index - 1]
            if getattr(t, "start", None) is not None:
                end_str = f"{int(t.end)}" if getattr(t, "end", None) is not None else "onwards"
                return f"Residential {self._sub_code_label} Tier {self._index} ({int(t.start)}-{end_str} kWh)"
            return f"Residential {self._sub_code_label} Tier {self._index} ({getattr(t, 'label', '')})"
        return f"Residential {self._sub_code_label} Tier {self._index}"

    @property
    def native_value(self):
        b = self._block(self._key)
        if b and hasattr(b, "tiers") and len(b.tiers) >= self._index:
            return getattr(b.tiers[self._index - 1], "rate", None)
        return None


class MeaTouRateSensor(MeaBase):
    """อัตราค่าพลังงาน TOU On Peak / Off Peak (บาท/kWh)."""

    _attr_native_unit_of_measurement = f"{CURRENCY}/kWh"
    _attr_icon = "mdi:clock-outline"
    _attr_suggested_display_precision = 4

    def __init__(self, coordinator: MeaTariffCoordinator, entry: ConfigEntry, block_key: str, peak_type: str) -> None:
        super().__init__(coordinator, entry)
        self._key, self._peak_type = block_key, peak_type
        self._attr_unique_id = f"{entry.entry_id}_{block_key}_{peak_type}"

        b_key = str(block_key)
        if "131" in b_key or "tou_131" in b_key:
            self._label = "1.3.1 (12-24 kV)"
        else:
            self._label = "1.3.2 (Under 12 kV)"

        self.entity_id = f"sensor.{ENTITY_ID_BASE}_{self._id_slug}_{peak_type}"
        self._attr_name = f"Residential {self._label} {peak_type.replace('_', ' ').title()}"

    @property
    def native_value(self):
        b = self._block(self._key)
        if not b:
            return None
        return getattr(b, self._peak_type, None)


class MeaTouStatusSensor(MeaBase):
    """Sensor บอกสถานะช่วงเวลา TOU (On Peak / Off Peak)."""

    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator: MeaTariffCoordinator, entry: ConfigEntry, block_key: str, folder_path: str) -> None:
        super().__init__(coordinator, entry)
        self._key = block_key
        self._folder_path = folder_path
        self._attr_unique_id = f"{entry.entry_id}_{block_key}_tou_time_status"
        self.entity_id = f"sensor.{ENTITY_ID_BASE}_{self._id_slug}_tou_time_status"
        self._attr_name = "TOU Time Status"

    @property
    def native_value(self) -> str:
        now = dt_util.now()
        date_str = now.strftime("%Y-%m-%d")

        # 1. เช็กวันหยุดราชการจากไฟล์
        holidays = load_holidays(self._folder_path)
        if date_str in holidays:
            return "Off Peak"

        # 2. เช็กวันเสาร์ (5) / อาทิตย์ (6)
        if now.weekday() in (5, 6):
            return "Off Peak"

        # 3. เช็กเวลา จันทร์ - ศุกร์ (09:00 - 22:00 น. คือ On Peak)
        start_peak = time(9, 0, 0)
        end_peak = time(22, 0, 0)
        current_time = now.time()

        if start_peak <= current_time < end_peak:
            return "On Peak"

        return "Off Peak"


class MeaServiceChargeSensor(MeaBase):
    """ค่าบริการรายเดือน."""

    _attr_native_unit_of_measurement = CURRENCY
    _attr_icon = "mdi:receipt-text-outline"

    def __init__(self, coordinator: MeaTariffCoordinator, entry: ConfigEntry, block_key: str) -> None:
        super().__init__(coordinator, entry)
        self._key = block_key
        self._attr_unique_id = f"{entry.entry_id}_{block_key}_service_charge"

        b_key = str(block_key)
        if "le150" in b_key:
            label = "1.1"
        elif "gt150" in b_key:
            label = "1.2"
        elif "131" in b_key or "tou_131" in b_key:
            label = "1.3.1 (12-24 kV)"
        elif "132" in b_key or "tou_132" in b_key:
            label = "1.3.2 (Under 12 kV)"
        else:
            label = b_key

        self.entity_id = f"sensor.{ENTITY_ID_BASE}_{self._id_slug}_service_charge"
        self._attr_name = f"Residential {label} Service Charge"

    @property
    def native_value(self):
        b = self._block(self._key)
        return getattr(b, "service_charge", None) if b else None


class MeaFtSensor(MeaBase):
    """ค่า Ft ปัจจุบัน (บาท/kWh)."""

    _attr_native_unit_of_measurement = f"{CURRENCY}/kWh"
    _attr_icon = "mdi:chart-line-variant"
    _attr_suggested_display_precision = 4

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_ft"
        self._attr_name = "Ft rate"
        self.entity_id = f"sensor.{ENTITY_ID_BASE}_{self._id_slug}_ft_rate"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("ft")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        ft = self.coordinator.data.get("ft")
        return {"satang_per_unit": round(ft * 100, 2) if ft is not None else None}