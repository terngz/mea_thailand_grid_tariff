"""MEA Thailand Grid Tariffs."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import CONF_SUB_TARIFF, CONF_TARIFF, DOMAIN, SERVICE_REFRESH
from .coordinator import MeaTariffCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = MeaTariffCoordinator(
        hass,
        entry.data[CONF_TARIFF],
        entry.data[CONF_SUB_TARIFF],
        entry.entry_id,
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):

        async def _handle_refresh(call: ServiceCall) -> None:
            for coord in hass.data.get(DOMAIN, {}).values():
                await coord.async_request_refresh()

        hass.services.async_register(
            DOMAIN, SERVICE_REFRESH, _handle_refresh, schema=vol.Schema({})
        )

    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)