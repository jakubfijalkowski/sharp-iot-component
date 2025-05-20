"""Support for Sharp IoT fans."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from sharp_core.states import OperatingMode
from sharp_devices.device_control import ChangeModeCommand

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SharpIoTDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Preset modes
PRESET_MODES = [
    "auto",
    "sleep",
    "low",
    "medium",
    "max",
    "pollen",
    "ion_shower",
    "sharp_life_air",
]

PRESET_TO_MODE = {
    "auto": OperatingMode.AUTO,
    "sleep": OperatingMode.SLEEP,
    "low": OperatingMode.LOW,
    "medium": OperatingMode.MED,
    "max": OperatingMode.MAX,
    "pollen": OperatingMode.POLLEN,
    "ion_shower": OperatingMode.ION_SHOWER,
    "sharp_life_air": OperatingMode.SHARP_LIFE_AIR,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sharp IoT fan entities."""
    coordinator: SharpIoTDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        device_data = coordinator.get_device_data(device_id)
        if device_data:
            device = device_data["device"]
            entities.append(SharpIoTFan(coordinator, device.box_id, device))

    async_add_entities(entities)


class SharpIoTFan(CoordinatorEntity, FanEntity):
    """Representation of a Sharp IoT fan."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the fan."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._attr_unique_id = f"{device_id}_fan"
        self._attr_name = f"Sharp Air Purifier {device_id[-4:]}"
        self._attr_supported_features = FanEntityFeature.PRESET_MODE
        self._attr_preset_modes = PRESET_MODES

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
        # Fan is unavailable when device is powered off
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f3_property:
            from sharp_core.states import PowerState
            return properties.f3_property.power == PowerState.ON
        return False

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f3_property:
            mode = properties.f3_property.operating_mode
            # Don't expose OFF mode - device power is handled by power switch
            if mode == OperatingMode.OFF:
                return None
            # Find preset mode that matches current operating mode
            for preset, op_mode in PRESET_TO_MODE.items():
                if op_mode == mode:
                    return preset
        return None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if preset_mode not in PRESET_TO_MODE:
            _LOGGER.error("Invalid preset mode: %s", preset_mode)
            return

        mode = PRESET_TO_MODE[preset_mode]
        command = ChangeModeCommand(mode)
        await self.coordinator.async_execute_command(self._device_id, command)