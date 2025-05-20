"""Support for Sharp IoT binary sensors."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from sharp_core.states import WaterContainerState

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SharpIoTDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sharp IoT binary sensor entities."""
    coordinator: SharpIoTDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        device_data = coordinator.get_device_data(device_id)
        if device_data:
            device = device_data["device"]
            entities.append(SharpWaterLevelSensor(coordinator, device_id, device))

    async_add_entities(entities)


class SharpWaterLevelSensor(CoordinatorEntity, BinarySensorEntity):
    """Water level binary sensor for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the water level sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._attr_unique_id = f"{device_id}_water_level"
        self._attr_name = f"Sharp {device_id[-4:]} Water Level"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:water"

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
        # Binary sensor unavailable when device is powered off
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f3_property:
            from sharp_core.states import PowerState
            return properties.f3_property.power == PowerState.ON
        return False

    @property
    def is_on(self) -> bool | None:
        """Return True if water level is low/empty (problem state)."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f2_property:
            # Return True for problem state (empty water container)
            return properties.f2_property.water_container == WaterContainerState.EMPTY
        return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f2_property:
            return {
                "water_container_state": properties.f2_property.water_container.name.lower()
            }
        return {}