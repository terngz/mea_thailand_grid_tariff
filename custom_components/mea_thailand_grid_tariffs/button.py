"""ปุ่ม Refresh — กดแล้วดึงข้อมูลใหม่ทันที ไม่ต้อง restart."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_SUB_TARIFF,
    DOMAIN,
    ENTITY_ID_BASE,
    INTEGRATION_NAME,
    sub_tariff_id_slug,
    sub_tariff_label,
)
from .coordinator import MeaTariffCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    add_entities([MeaRefreshButton(hass.data[DOMAIN][entry.entry_id], entry)])


class MeaRefreshButton(CoordinatorEntity[MeaTariffCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Refresh tariffs"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        sub_tariff = str(entry.data.get(CONF_SUB_TARIFF, "")).strip().lower()
        id_slug = sub_tariff_id_slug(sub_tariff)

        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self._attr_suggested_object_id = f"{ENTITY_ID_BASE}_{id_slug}_refresh"

        # ใช้ label เดียวกับที่ sensor.py ตั้งไว้ (sub_tariff เฉพาะ, ตามภาษาระบบ) ไม่ใช่ชื่อ
        # หน้าเว็บทั่วไป (coordinator.data['name']) — เพราะ device เดียวกัน (identifiers ชุดเดียวกัน)
        # ถ้าไม่ตรงกัน ตัวที่โหลดทีหลัง (button มาหลัง sensor ตาม PLATFORMS ใน __init__.py)
        # จะไปเขียนทับชื่อที่ถูกต้องของ sensor.py ทิ้ง
        language = getattr(coordinator.hass.config, "language", None)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            model=INTEGRATION_NAME,
            name=f"MEA {sub_tariff_label(sub_tariff, language)}",
        )

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()