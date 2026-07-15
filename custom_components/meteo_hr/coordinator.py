"""Data update coordinator for the Meteo.hr weather integration."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from xml.etree import ElementTree

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .const import CONF_CITY_CODE, DEFAULT_CITY_CODE, FORECAST_URL, SYMBOLS_URL, UPDATE_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)

# Beaufort-ish midpoint speeds (km/h) for meteo.hr's 4 wind intensity levels.
_WIND_SPEED_KMH = {0: 0, 1: 10, 2: 20, 3: 35, 4: 55}
_WIND_BEARING_DEG = {
    "N": 0, "NE": 45, "E": 90, "SE": 135,
    "S": 180, "SW": 225, "W": 270, "NW": 315,
}
_WIND_RE = re.compile(r"^(N|NE|E|SE|S|SW|W|NW|C)(\d)$")


def _parse_wind(code: str) -> tuple[float | None, float | None]:
    """Parse a meteo.hr wind code like 'NE1' or 'C0' into (speed_kmh, bearing_deg)."""
    match = _WIND_RE.match((code or "").strip())
    if not match:
        return None, None
    direction, intensity = match.group(1), int(match.group(2))
    speed = _WIND_SPEED_KMH.get(intensity)
    bearing = _WIND_BEARING_DEG.get(direction)
    return speed, bearing


def classify_condition(description: str, night: bool) -> str:
    """Map a meteo.hr Croatian symbol description to an HA weather condition."""
    text = (description or "").lower()

    def has(*words: str) -> bool:
        return all(word in text for word in words)

    if has("snijeg", "kiš"):
        condition = "snowy-rainy"
    elif has("snijeg"):
        condition = "snowy"
    elif has("grmljavin", "kiš"):
        condition = "lightning-rainy"
    elif has("grmljavin"):
        condition = "lightning"
    elif has("kiš") and "znatnu" in text:
        condition = "pouring"
    elif has("kiš"):
        condition = "rainy"
    elif "maglovit" in text or "magla" in text:
        condition = "fog"
    elif "potpuno oblačno" in text:
        condition = "cloudy"
    elif "pretežno oblačno" in text or "oblačno, ali svijetlo" in text:
        condition = "cloudy"
    elif "umjereno oblačno" in text or "malo oblačno" in text:
        condition = "partlycloudy"
    elif "vedro" in text:
        condition = "clear-night"
    elif "sunčano" in text:
        condition = "sunny"
    else:
        condition = "partlycloudy"

    if condition == "sunny" and night:
        condition = "clear-night"
    return condition


class MeteoHrCoordinator(DataUpdateCoordinator[list[dict]]):
    """Fetch and parse the meteo.hr 7-day hourly forecast for one city."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"meteo_hr_{entry.entry_id}",
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self.entry = entry
        self._symbols: dict[str, str] = {}

    @property
    def city_code(self) -> str:
        return self.entry.data.get(CONF_CITY_CODE, DEFAULT_CITY_CODE)

    async def _async_update_data(self) -> list[dict]:
        session = async_get_clientsession(self.hass)

        if not self._symbols:
            try:
                async with session.get(SYMBOLS_URL) as resp:
                    resp.raise_for_status()
                    self._symbols = await resp.json(content_type=None)
            except Exception as err:  # noqa: BLE001
                raise UpdateFailed(f"Error fetching meteo.hr symbol table: {err}") from err

        try:
            async with session.get(FORECAST_URL) as resp:
                resp.raise_for_status()
                raw = await resp.read()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error fetching meteo.hr forecast: {err}") from err

        try:
            root = ElementTree.fromstring(raw)
        except ElementTree.ParseError as err:
            raise UpdateFailed(f"Error parsing meteo.hr forecast XML: {err}") from err

        grad = root.find(f".//grad[@code='{self.city_code}']")
        if grad is None:
            raise UpdateFailed(f"City code '{self.city_code}' not found in meteo.hr forecast")

        tzinfo = dt_util.get_time_zone(self.hass.config.time_zone)
        hourly: list[dict] = []
        for dan in grad.findall("dan"):
            datum = dan.get("datum", "")
            sat = dan.get("sat", "0")
            try:
                day = datetime.strptime(datum, "%d.%m.%Y.")
                when = day.replace(hour=int(sat), tzinfo=tzinfo)
            except ValueError:
                continue

            symbol = (dan.findtext("simbol") or "").strip()
            temp = dan.findtext("t_2m")
            precip = dan.findtext("oborina")
            prob = dan.findtext("vjerojatnost")
            wind_speed, wind_bearing = _parse_wind(dan.findtext("vjetar") or "")

            description = self._symbols.get(symbol, "")
            hourly.append(
                {
                    "datetime": when,
                    "temperature": float(temp) if temp else None,
                    "condition": classify_condition(description, symbol.endswith("n")),
                    "precipitation": float(precip) if precip else 0.0,
                    "precipitation_probability": int(float(prob)) if prob else 0,
                    "wind_speed": wind_speed,
                    "wind_bearing": wind_bearing,
                }
            )

        if not hourly:
            raise UpdateFailed(f"No forecast hours parsed for '{self.city_code}'")

        hourly.sort(key=lambda item: item["datetime"])
        return hourly
