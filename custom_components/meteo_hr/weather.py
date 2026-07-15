"""Weather platform for the Meteo.hr integration."""
from __future__ import annotations

from collections import defaultdict

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPrecipitationDepth, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import MeteoHrCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: MeteoHrCoordinator = hass.data[DOMAIN][entry.entry_id]["weather"]
    async_add_entities([MeteoHrWeather(coordinator, entry)])


def _closest_hour(hourly: list[dict], now) -> dict | None:
    if not hourly:
        return None
    return min(hourly, key=lambda item: abs((item["datetime"] - now).total_seconds()))


class MeteoHrWeather(CoordinatorEntity[MeteoHrCoordinator], WeatherEntity):
    """Weather entity backed by the meteo.hr 7-day hourly forecast."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(self, coordinator: MeteoHrCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.city_code}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title or DEFAULT_NAME,
            "manufacturer": "DHMZ / meteo.hr",
        }

    @property
    def _current(self) -> dict | None:
        return _closest_hour(self.coordinator.data or [], dt_util.now())

    @property
    def condition(self) -> str | None:
        current = self._current
        return current["condition"] if current else None

    @property
    def native_temperature(self) -> float | None:
        current = self._current
        return current["temperature"] if current else None

    @property
    def native_wind_speed(self) -> float | None:
        current = self._current
        return current["wind_speed"] if current else None

    @property
    def wind_bearing(self) -> float | None:
        current = self._current
        return current["wind_bearing"] if current else None

    async def async_forecast_daily(self) -> list[Forecast]:
        by_day: dict[str, list[dict]] = defaultdict(list)
        for hour in self.coordinator.data or []:
            by_day[hour["datetime"].date().isoformat()].append(hour)

        forecasts: list[Forecast] = []
        for _, hours in sorted(by_day.items()):
            hours.sort(key=lambda item: item["datetime"])
            noonish = min(hours, key=lambda item: abs(item["datetime"].hour - 12))
            temps = [h["temperature"] for h in hours if h["temperature"] is not None]
            forecasts.append(
                Forecast(
                    datetime=hours[0]["datetime"].isoformat(),
                    condition=noonish["condition"],
                    native_temperature=max(temps) if temps else None,
                    native_templow=min(temps) if temps else None,
                    native_precipitation=round(sum(h["precipitation"] for h in hours), 1),
                    precipitation_probability=max(
                        h["precipitation_probability"] for h in hours
                    ),
                    wind_bearing=noonish["wind_bearing"],
                    native_wind_speed=noonish["wind_speed"],
                )
            )
        return forecasts

    async def async_forecast_hourly(self) -> list[Forecast]:
        return [
            Forecast(
                datetime=hour["datetime"].isoformat(),
                condition=hour["condition"],
                native_temperature=hour["temperature"],
                native_precipitation=hour["precipitation"],
                precipitation_probability=hour["precipitation_probability"],
                wind_bearing=hour["wind_bearing"],
                native_wind_speed=hour["wind_speed"],
            )
            for hour in self.coordinator.data or []
        ]
