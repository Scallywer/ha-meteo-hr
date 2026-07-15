"""Sensor platform for the Meteo.hr integration — real station observations.

These sensors are independent of (and additive to) the weather.* forecast entity:
they come from live station readings (current conditions + UV index), not the
forecast model, refreshed on their own 30-minute cycle via ObservationsCoordinator.
"""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import ObservationsCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ObservationsCoordinator = hass.data[DOMAIN][entry.entry_id]["observations"]
    async_add_entities(
        [
            MeteoHrTemperatureSensor(coordinator, entry),
            MeteoHrWindSpeedSensor(coordinator, entry),
            MeteoHrWindBearingSensor(coordinator, entry),
            MeteoHrConditionTextSensor(coordinator, entry),
            MeteoHrUvIndexSensor(coordinator, entry),
        ]
    )


class _MeteoHrObservationSensor(CoordinatorEntity[ObservationsCoordinator], SensorEntity):
    """Common device wiring for all observation sensors on one config entry."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ObservationsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title or DEFAULT_NAME,
            "manufacturer": "DHMZ / meteo.hr",
        }


class MeteoHrTemperatureSensor(_MeteoHrObservationSensor):
    """Real station temperature reading (current conditions table)."""

    _attr_name = "Station temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ObservationsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_station_temperature"

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("temperature")

    @property
    def extra_state_attributes(self) -> dict:
        return {"station": (self.coordinator.data or {}).get("matched_station_conditions")}


class MeteoHrWindSpeedSensor(_MeteoHrObservationSensor):
    """Real station wind speed reading (current conditions table)."""

    _attr_name = "Station wind speed"
    _attr_device_class = SensorDeviceClass.WIND_SPEED
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ObservationsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_station_wind_speed"

    @property
    def native_value(self) -> float | None:
        value = (self.coordinator.data or {}).get("wind_speed")
        return round(value, 1) if value is not None else None


class MeteoHrWindBearingSensor(_MeteoHrObservationSensor):
    """Real station wind bearing reading (current conditions table)."""

    _attr_name = "Station wind bearing"
    _attr_native_unit_of_measurement = "°"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ObservationsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_station_wind_bearing"

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("wind_bearing")


class MeteoHrConditionTextSensor(_MeteoHrObservationSensor):
    """Raw Croatian sky-condition text from the current-conditions table."""

    _attr_name = "Station condition"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ObservationsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_station_condition_text"

    @property
    def native_value(self) -> str | None:
        return (self.coordinator.data or {}).get("condition_text")


class MeteoHrUvIndexSensor(_MeteoHrObservationSensor):
    """Current-hour UV index; today's full hourly series as an attribute."""

    _attr_name = "UV index"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:weather-sunny-alert"

    def __init__(self, coordinator: ObservationsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_uv_index"

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("uv_index")

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "station": data.get("matched_station_uv"),
            "hourly": data.get("uv_hourly", {}),
        }
