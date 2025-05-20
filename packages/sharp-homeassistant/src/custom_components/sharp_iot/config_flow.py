"""Config flow for Sharp IoT integration."""
from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from sharp_core import SharpClient
from sharp_devices.operations import SharpOperations

from .const import DOMAIN, CONF_TERMINAL_ID

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TERMINAL_ID): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    terminal_id = data[CONF_TERMINAL_ID]

    # Test the connection by setting up operations
    client = SharpClient()
    operations = SharpOperations(client)

    try:
        # Test the terminal ID by attempting to set up operations
        success = await hass.async_add_executor_job(
            operations.setup_with_terminal_id, terminal_id
        )

        if not success:
            raise InvalidAuth

        # Test device discovery
        devices = await hass.async_add_executor_job(
            operations.discover_and_pair_devices, terminal_id
        )

        if not devices:
            raise CannotConnect

    except Exception:
        _LOGGER.exception("Unexpected exception")
        raise CannotConnect

    # Return info that you want to store in the config entry.
    return {"title": f"Sharp IoT ({len(devices)} devices)", "devices_count": len(devices)}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sharp IoT."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_TERMINAL_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""