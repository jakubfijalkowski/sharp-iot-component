"""Support for Sharp IoT sensors."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    UnitOfTemperature,
)

from .lib.sharp_core.states import QualityLevel

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SharpIoTDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Quality level mapping to numeric values for HA
QUALITY_LEVEL_VALUES = {
    QualityLevel.CLEAN: 0,
    QualityLevel.LOW: 1,
    QualityLevel.MEDIUM: 2,
    QualityLevel.HIGH: 3,
    QualityLevel.VERY_HIGH: 4,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sharp IoT sensor entities."""
    coordinator: SharpIoTDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        device_data = coordinator.get_device_data(device_id)
        if device_data:
            device = device_data["device"]

            # Environmental sensors (F1 property)
            entities.extend([
                SharpTemperatureSensor(coordinator, device_id, device),
                SharpHumiditySensor(coordinator, device_id, device),
                SharpPM25Sensor(coordinator, device_id, device),
            ])

            # Quality sensors (F2 property)
            entities.extend([
                SharpAirQualitySensor(coordinator, device_id, device),
                SharpDustLevelSensor(coordinator, device_id, device),
                SharpOdorLevelSensor(coordinator, device_id, device),
            ])

    async_add_entities(entities)


class SharpSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Sharp IoT sensors."""

    def __init__(self, coordinator, device_id, device, sensor_type):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{device_id}_{sensor_type}"
        self._attr_name = f"Sharp {device_id[-4:]} {sensor_type.replace('_', ' ').title()}"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"Sharp Air Purifier {self._device_id[-4:]}",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.is_device_available(self._device_id):
            return False
        # Sensors unavailable when device is powered off
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f3_property:
            from .lib.sharp_core.states import PowerState
            return properties.f3_property.power == PowerState.ON
        return False


class SharpTemperatureSensor(SharpSensorBase):
    """Temperature sensor for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the temperature sensor."""
        super().__init__(coordinator, device_id, device, "temperature")
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the temperature value."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f1_property:
            return float(properties.f1_property.temperature)
        return None


class SharpHumiditySensor(SharpSensorBase):
    """Humidity sensor for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the humidity sensor."""
        super().__init__(coordinator, device_id, device, "humidity")
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the humidity value."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f1_property:
            return float(properties.f1_property.humidity)
        return None


class SharpPM25Sensor(SharpSensorBase):
    """PM2.5 sensor for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the PM2.5 sensor."""
        super().__init__(coordinator, device_id, device, "pm25")
        self._attr_device_class = SensorDeviceClass.PM25
        self._attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the PM2.5 value."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f1_property:
            return float(properties.f1_property.pm25_level)
        return None


class SharpAirQualitySensor(SharpSensorBase):
    """Air quality sensor for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the air quality sensor."""
        super().__init__(coordinator, device_id, device, "air_quality")
        self._attr_device_class = SensorDeviceClass.AQI
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the air quality value."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f2_property:
            return QUALITY_LEVEL_VALUES.get(properties.f2_property.air_quality)
        return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f2_property:
            return {
                "quality_level": properties.f2_property.air_quality.name.lower()
            }
        return {}


class SharpDustLevelSensor(SharpSensorBase):
    """Dust level sensor for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the dust level sensor."""
        super().__init__(coordinator, device_id, device, "dust_level")
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the dust level value."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f2_property:
            return QUALITY_LEVEL_VALUES.get(properties.f2_property.dust_level)
        return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f2_property:
            return {
                "quality_level": properties.f2_property.dust_level.name.lower()
            }
        return {}


class SharpOdorLevelSensor(SharpSensorBase):
    """Odor level sensor for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the odor level sensor."""
        super().__init__(coordinator, device_id, device, "odor_level")
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the odor level value."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f2_property:
            return QUALITY_LEVEL_VALUES.get(properties.f2_property.odor_level)
        return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f2_property:
            return {
                "quality_level": properties.f2_property.odor_level.name.lower()
            }
        return {}