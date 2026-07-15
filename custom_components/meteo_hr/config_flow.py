"""Config flow for the Meteo.hr weather integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from . import scrape
from .const import (
    CITY_LIST_URL,
    CONDITIONS_URL,
    CONF_CITY_CODE,
    CONF_STATION_NAME,
    DEFAULT_CITY_CODE,
    DEFAULT_NAME,
    DEFAULT_STATION_NAME,
    DOMAIN,
    UV_INDEX_URL,
)

_LOGGER = logging.getLogger(__name__)


async def _fetch_city_options(session) -> list[SelectOptionDict]:
    """Live-fetch the forecast page's own city dropdown (~323 entries)."""
    async with session.get(CITY_LIST_URL) as resp:
        resp.raise_for_status()
        html = await resp.text()
    options = scrape.parse_select_options(html, "menprog")
    return [
        SelectOptionDict(value=value, label=label)
        for value, label in sorted(options, key=lambda o: o[1])
    ]


async def _fetch_station_options(session) -> list[SelectOptionDict]:
    """Live-fetch stations present in BOTH the current-conditions and UV tables.

    The two source pages don't share a consistent station list (verified: 5 of the
    UV table's 20 stations have no match at all in the 76-station conditions table)
    — offering anything outside the intersection could leave one sensor set
    permanently unavailable, so only mutually-present stations are offered.
    """
    async with session.get(CONDITIONS_URL) as resp:
        resp.raise_for_status()
        conditions_html = await resp.text()
    async with session.get(UV_INDEX_URL) as resp:
        resp.raise_for_status()
        uv_html = await resp.text()

    conditions_names = [
        row[0] for row in scrape.parse_table_rows(scrape.table_body_html(conditions_html))
    ]
    uv_names = [row[0] for row in scrape.parse_table_rows(scrape.table_body_html(uv_html))]

    normalized_conditions = {scrape.normalize_station_name(n) for n in conditions_names}
    intersection = [
        name
        for name in uv_names
        if any(
            c.startswith(scrape.normalize_station_name(name)) for c in normalized_conditions
        )
    ]
    return [SelectOptionDict(value=name, label=name) for name in sorted(intersection)]


def _schema(
    defaults: dict[str, Any],
    city_options: list[SelectOptionDict] | None,
    station_options: list[SelectOptionDict] | None,
) -> vol.Schema:
    city_selector: Any = str
    if city_options:
        city_selector = SelectSelector(
            SelectSelectorConfig(options=city_options, mode=SelectSelectorMode.DROPDOWN)
        )

    station_selector: Any = str
    if station_options:
        station_selector = SelectSelector(
            SelectSelectorConfig(options=station_options, mode=SelectSelectorMode.DROPDOWN)
        )

    return vol.Schema(
        {
            vol.Required("name", default=defaults.get("name", DEFAULT_NAME)): str,
            vol.Required(
                CONF_CITY_CODE, default=defaults.get(CONF_CITY_CODE, DEFAULT_CITY_CODE)
            ): city_selector,
            vol.Required(
                CONF_STATION_NAME,
                default=defaults.get(CONF_STATION_NAME, DEFAULT_STATION_NAME),
            ): station_selector,
        }
    )


class MeteoHrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Meteo.hr weather."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        session = async_get_clientsession(self.hass)

        try:
            city_options = await _fetch_city_options(session)
        except Exception:  # noqa: BLE001
            _LOGGER.warning("Could not live-fetch meteo.hr city list; falling back to free text")
            city_options = None

        try:
            station_options = await _fetch_station_options(session)
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Could not live-fetch meteo.hr station list; falling back to free text"
            )
            station_options = None

        if user_input is not None:
            city_code = user_input[CONF_CITY_CODE].strip().upper()
            station_name = user_input[CONF_STATION_NAME].strip()
            await self.async_set_unique_id(city_code)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input["name"],
                data={
                    "name": user_input["name"],
                    CONF_CITY_CODE: city_code,
                    CONF_STATION_NAME: station_name,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema({}, city_options, station_options),
            errors=errors,
        )
