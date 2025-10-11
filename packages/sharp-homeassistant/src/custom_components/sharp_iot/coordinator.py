"""DataUpdateCoordinator for Sharp IoT integration."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from sharp_core import SharpClient
from sharp_devices.operations import SharpOperations, BoxInfo
from sharp_devices.device_properties import DeviceProperties

from .const import DOMAIN, CONF_TERMINAL_ID, UPDATE_INTERVAL, TERMINAL_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SharpIoTDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Sharp IoT API."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize."""
        self.terminal_id = config[CONF_TERMINAL_ID]
        self.client = SharpClient()
        self.operations = SharpOperations(self.client)
        self.devices: list[BoxInfo] = []
        self.last_terminal_refresh: float = 0

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # Setup operations with terminal ID once per day (or on first run)
            current_time = time.time()
            if current_time - self.last_terminal_refresh >= TERMINAL_REFRESH_INTERVAL:
                await self.hass.async_add_executor_job(
                    self.operations.setup_with_terminal_id, self.terminal_id
                )
                self.last_terminal_refresh = current_time
                _LOGGER.debug("Terminal ID refreshed with server")

            # Discover devices on first run or if no devices
            if not self.devices:
                self.devices = await self.hass.async_add_executor_job(
                    self.operations.discover_and_pair_devices, self.terminal_id
                )
                _LOGGER.debug("Discovered %d devices", len(self.devices))

            # Fetch data for all devices
            device_data = {}
            for device in self.devices:
                try:
                    properties = await self.hass.async_add_executor_job(
                        self.operations.get_device_properties, device
                    )
                    device_data[device.box_id] = {
                        "device": device,
                        "properties": properties,
                        "available": True,
                    }
                    _LOGGER.debug(
                        "Updated data for device %s",
                        properties
                    )
                except Exception as ex:
                    device_label = device.box_id[-4:] if device.box_id else "unknown"
                    _LOGGER.warning(
                        "Failed to update device %s: %s", device_label, ex
                    )
                    device_data[device.box_id] = {
                        "device": device,
                        "properties": None,
                        "available": False,
                    }

            return device_data

        except Exception as ex:
            _LOGGER.error("Error communicating with Sharp IoT API: %s", ex)
            raise UpdateFailed(f"Error communicating with API: {ex}") from ex

    async def async_execute_command(self, device_id: str, operation) -> bool:
        """Execute a command on a specific device."""
        device = None
        for dev in self.devices:
            if dev.box_id == device_id:
                device = dev
                break

        if not device:
            _LOGGER.error("Device %s not found", device_id)
            return False

        try:
            success = await self.hass.async_add_executor_job(
                self.operations.execute_operation,
                device,
                self.terminal_id,
                operation
            )

            if success:
                # Refresh data after command execution
                await self.async_request_refresh()

            return success
        except Exception as ex:
            _LOGGER.error("Error executing command on device %s: %s", device_id, ex)
            return False

    def get_device_data(self, device_id: str) -> dict[str, Any] | None:
        """Get data for a specific device."""
        return self.data.get(device_id) if self.data else None

    def get_device_properties(self, device_id: str) -> DeviceProperties | None:
        """Get properties for a specific device."""
        device_data = self.get_device_data(device_id)
        return device_data.get("properties") if device_data else None

    def is_device_available(self, device_id: str) -> bool:
        """Check if a device is available."""
        device_data = self.get_device_data(device_id)
        return device_data.get("available", False) if device_data else False