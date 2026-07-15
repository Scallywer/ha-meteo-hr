"""Config flow for the Meteo.hr weather integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_CITY_CODE, DEFAULT_CITY_CODE, DEFAULT_NAME, DOMAIN


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("name", default=defaults.get("name", DEFAULT_NAME)): str,
            vol.Required(
                CONF_CITY_CODE, default=defaults.get(CONF_CITY_CODE, DEFAULT_CITY_CODE)
            ): str,
        }
    )


class MeteoHrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Meteo.hr weather."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            city_code = user_input[CONF_CITY_CODE].strip().upper()
            await self.async_set_unique_id(city_code)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input["name"],
                data={"name": user_input["name"], CONF_CITY_CODE: city_code},
            )

        return self.async_show_form(
            step_id="user", data_schema=_schema({}), errors=errors
        )
