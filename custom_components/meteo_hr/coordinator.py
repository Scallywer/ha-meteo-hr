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

from . import scrape
from .const import (
    CONDITIONS_URL,
    CONF_CITY_CODE,
    CONF_STATION_NAME,
    DEFAULT_CITY_CODE,
    DEFAULT_STATION_NAME,
    FORECAST_URL,
    OBSERVATIONS_UPDATE_INTERVAL_MINUTES,
    SYMBOLS_URL,
    UPDATE_INTERVAL_MINUTES,
    UV_INDEX_URL,
)

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


class ObservationsCoordinator(DataUpdateCoordinator[dict]):
    """Fetch real station observations (current conditions + UV index) for one station.

    Independent of MeteoHrCoordinator: different source pages, different refresh
    cadence, and failure here never affects the forecast weather entity.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"meteo_hr_observations_{entry.entry_id}",
            update_interval=timedelta(minutes=OBSERVATIONS_UPDATE_INTERVAL_MINUTES),
        )
        self.entry = entry

    @property
    def station_name(self) -> str:
        return self.entry.data.get(CONF_STATION_NAME, DEFAULT_STATION_NAME)

    async def _async_update_data(self) -> dict:
        session = async_get_clientsession(self.hass)
        station = self.station_name

        try:
            async with session.get(CONDITIONS_URL) as resp:
                resp.raise_for_status()
                conditions_html = await resp.text()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error fetching meteo.hr current conditions: {err}") from err

        try:
            async with session.get(UV_INDEX_URL) as resp:
                resp.raise_for_status()
                uv_html = await resp.text()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error fetching meteo.hr UV index: {err}") from err

        conditions_rows = scrape.parse_table_rows(scrape.table_body_html(conditions_html))
        conditions_row = scrape.find_station_row(conditions_rows, station)
        if conditions_row is None:
            raise UpdateFailed(
                f"Station '{station}' not found in meteo.hr current-conditions table"
            )

        uv_headers = scrape.parse_table_header(uv_html)
        uv_rows = scrape.parse_table_rows(scrape.table_body_html(uv_html))
        uv_row = scrape.find_station_row(uv_rows, station)
        if uv_row is None:
            raise UpdateFailed(f"Station '{station}' not found in meteo.hr UV index table")

        _, wind_dir, wind_speed_ms, temp, condition_text = conditions_row[:5]
        wind_bearing = _WIND_BEARING_DEG.get(wind_dir.strip().upper())
        try:
            wind_speed_kmh = float(wind_speed_ms) * 3.6
        except ValueError:
            wind_speed_kmh = None
        try:
            temperature = float(temp)
        except ValueError:
            temperature = None

        # uv_row = [station_name, altitude, <one value per header column after "Postaja">]
        hour_labels = uv_headers[1:]
        hour_values = uv_row[2:]
        uv_hourly = {
            label: float(value)
            for label, value in zip(hour_labels, hour_values)
            if value not in ("", "-")
        }
        uv_index = list(uv_hourly.values())[-1] if uv_hourly else None

        return {
            "matched_station_conditions": conditions_row[0],
            "temperature": temperature,
            "wind_speed": wind_speed_kmh,
            "wind_bearing": wind_bearing,
            "condition_text": condition_text,
            "matched_station_uv": uv_row[0],
            "uv_index": uv_index,
            "uv_hourly": uv_hourly,
        }
