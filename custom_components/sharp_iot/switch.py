"""Support for Sharp IoT switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .lib.sharp_core.states import ChildLockState, LEDBrightnessState, PowerState, HumidificationState
from .lib.sharp_devices.device_control import ChildLockCommand, LEDBrightnessCommand, PowerOperation, HumidificationCommand

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SharpIoTDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sharp IoT switch entities."""
    coordinator: SharpIoTDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        device_data = coordinator.get_device_data(device_id)
        if device_data:
            device = device_data["device"]
            entities.extend([
                SharpPowerSwitch(coordinator, device_id, device),
                SharpHumidificationSwitch(coordinator, device_id, device),
                SharpChildLockSwitch(coordinator, device_id, device),
                SharpLEDBrightnessSwitch(coordinator, device_id, device),
            ])

    async_add_entities(entities)


class SharpSwitchBase(CoordinatorEntity, SwitchEntity):
    """Base class for Sharp IoT switches."""

    def __init__(self, coordinator, device_id, device, switch_type):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._switch_type = switch_type
        self._attr_unique_id = f"{device_id}_{switch_type}"
        self._attr_name = f"Sharp {device_id[-4:]} {switch_type.replace('_', ' ').title()}"

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
        # For power switch, always available when coordinator has data
        # For other switches, check if device is powered on
        if self._switch_type == "power":
            return True
        # Other switches unavailable when device is powered off
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f3_property:
            return properties.f3_property.power == PowerState.ON
        return False


class SharpPowerSwitch(SharpSwitchBase):
    """Power switch for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the power switch."""
        super().__init__(coordinator, device_id, device, "power")
        self._attr_icon = "mdi:power"

    @property
    def is_on(self) -> bool | None:
        """Return True if device is on."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f3_property:
            return properties.f3_property.power == PowerState.ON
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the device."""
        operation = PowerOperation(PowerState.ON)
        await self.coordinator.async_execute_command(self._device_id, operation)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the device."""
        operation = PowerOperation(PowerState.OFF)
        await self.coordinator.async_execute_command(self._device_id, operation)


class SharpHumidificationSwitch(SharpSwitchBase):
    """Humidification switch for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the humidification switch."""
        super().__init__(coordinator, device_id, device, "humidification")
        self._attr_icon = "mdi:water"

    @property
    def is_on(self) -> bool | None:
        """Return True if humidification is on."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f3_property:
            return properties.f3_property.humidification == HumidificationState.ON
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on humidification."""
        command = HumidificationCommand(HumidificationState.ON)
        await self.coordinator.async_execute_command(self._device_id, command)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off humidification."""
        command = HumidificationCommand(HumidificationState.OFF)
        await self.coordinator.async_execute_command(self._device_id, command)


class SharpChildLockSwitch(SharpSwitchBase):
    """Child lock switch for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the child lock switch."""
        super().__init__(coordinator, device_id, device, "child_lock")
        self._attr_icon = "mdi:lock"

    @property
    def is_on(self) -> bool | None:
        """Return True if child lock is on."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f3_property:
            return properties.f3_property.child_lock == ChildLockState.ON
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on child lock."""
        command = ChildLockCommand(ChildLockState.ON)
        await self.coordinator.async_execute_command(self._device_id, command)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off child lock."""
        command = ChildLockCommand(ChildLockState.OFF)
        await self.coordinator.async_execute_command(self._device_id, command)


class SharpLEDBrightnessSwitch(SharpSwitchBase):
    """LED brightness switch for Sharp IoT device."""

    def __init__(self, coordinator, device_id, device):
        """Initialize the LED brightness switch."""
        super().__init__(coordinator, device_id, device, "led_brightness")
        self._attr_icon = "mdi:lightbulb"

    @property
    def is_on(self) -> bool | None:
        """Return True if LED brightness is not off."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f3_property:
            return properties.f3_property.led_brightness != LEDBrightnessState.OFF
        return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        properties = self.coordinator.get_device_properties(self._device_id)
        if properties and properties.f3_property:
            return {
                "brightness_level": properties.f3_property.led_brightness.name.lower()
            }
        return {}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on LED brightness (set to auto)."""
        command = LEDBrightnessCommand(LEDBrightnessState.AUTO)
        await self.coordinator.async_execute_command(self._device_id, command)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off LED brightness."""
        command = LEDBrightnessCommand(LEDBrightnessState.OFF)
        await self.coordinator.async_execute_command(self._device_id, command)