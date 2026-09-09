"""Config flow ของ MEA Thailand Grid Tariffs."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_SUB_TARIFF,
    CONF_TARIFF,
    DOMAIN,
    residential_title,
)


class MeaTariffConfigFlow(ConfigFlow, domain=DOMAIN):
    """จัดการขั้นตอนเพิ่ม integration."""

    VERSION = 1

    def __init__(self) -> None:
        self._selected_tariff: str = "residential"

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            sub_key = user_input[CONF_SUB_TARIFF]
            tariff_key = self._selected_tariff
            unique_id = f"{tariff_key}_{sub_key}"

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=residential_title(self.hass.config.language),
                data={
                    CONF_TARIFF: "residential",
                    CONF_SUB_TARIFF: sub_key,
                },
            )

        # กำหนดเฉพาะ value ใน options แล้วให้ Home Assistant ดึง Label จาก selector.sub_tariff.options ตามภาษาของผู้ใช้
        schema = vol.Schema(
            {
                vol.Required(CONF_SUB_TARIFF, default="gt150"): SelectSelector(
                    SelectSelectorConfig(
                        options=["le150", "gt150", "tou_131", "tou_132"],
                        mode=SelectSelectorMode.LIST,
                        translation_key="sub_tariff",
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)