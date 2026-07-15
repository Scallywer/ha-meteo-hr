"""The Meteo.hr weather integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import MeteoHrCoordinator, ObservationsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.WEATHER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    weather_coordinator = MeteoHrCoordinator(hass, entry)
    await weather_coordinator.async_config_entry_first_refresh()

    observations_coordinator = ObservationsCoordinator(hass, entry)
    try:
        await observations_coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as err:
        # Observation sensors are independent of the forecast weather entity —
        # a failure here (e.g. meteo.hr page layout change) shouldn't block it.
        _LOGGER.warning("Meteo.hr observation sensors unavailable at startup: %s", err)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "weather": weather_coordinator,
        "observations": observations_coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
