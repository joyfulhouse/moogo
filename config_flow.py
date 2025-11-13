"""Config flow for Moogo integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .moogo_api import MoogoClient
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Basic config flow for email/password authentication or public data only
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_EMAIL, default=""): str,
        vol.Optional(CONF_PASSWORD, default=""): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    session = async_get_clientsession(hass)
    
    api = MoogoClient(
        email=data.get(CONF_EMAIL),
        password=data.get(CONF_PASSWORD),
        session=session
    )

    # Test public endpoints first (always works)
    if not await api.test_connection():
        raise CannotConnect

    # If credentials provided, test authentication
    if data.get(CONF_EMAIL) and data.get(CONF_PASSWORD):
        if not await api.authenticate():
            raise InvalidAuth
        title = f"Moogo ({data[CONF_EMAIL]})"
    else:
        title = "Moogo (Public Data Only)"

    return {"title": title}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Moogo."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", 
                data_schema=STEP_USER_DATA_SCHEMA,
                description_placeholders={
                    "note": "Leave email and password empty for public data only (liquid types and schedules). Enter credentials for full device control."
                }
            )

        errors = {}

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
            # Set unique ID based on authentication mode
            if user_input.get(CONF_EMAIL) and user_input.get(CONF_PASSWORD):
                await self.async_set_unique_id(user_input[CONF_EMAIL])
            else:
                await self.async_set_unique_id("public_data")

            # Prevent duplicate entries
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "note": "Leave email and password empty for public data only (liquid types and schedules). Enter credentials for full device control."
            }
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle reauthentication when credentials expire or fail."""
        self.entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthentication confirmation."""
        errors = {}

        if user_input is not None:
            # Validate the new credentials
            try:
                # Get existing email from entry if not provided
                email = user_input.get(CONF_EMAIL) or self.entry.data.get(CONF_EMAIL)
                password = user_input.get(CONF_PASSWORD)

                if not email or not password:
                    errors["base"] = "invalid_auth"
                else:
                    # Validate credentials
                    validation_data = {
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                    }
                    await validate_input(self.hass, validation_data)

                    # Update the config entry with new credentials
                    self.hass.config_entries.async_update_entry(
                        self.entry,
                        data={
                            **self.entry.data,
                            CONF_EMAIL: email,
                            CONF_PASSWORD: password,
                        },
                    )

                    # Reload the config entry to apply new credentials
                    await self.hass.config_entries.async_reload(self.entry.entry_id)

                    return self.async_abort(reason="reauth_successful")

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"

        # Show the reauth form
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=self.entry.data.get(CONF_EMAIL, "")): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            errors = {}

            try:
                # Validate new credentials or public data mode
                info = await validate_input(self.hass, user_input)

                # Update the config entry with new data
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=user_input,
                    title=info["title"],
                )

                # Reload the config entry to apply new settings
                await self.hass.config_entries.async_reload(entry.entry_id)

                return self.async_abort(reason="reconfigure_successful")

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reconfiguration")
                errors["base"] = "unknown"

            # Show form again with errors
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=vol.Schema(
                    {
                        vol.Optional(CONF_EMAIL, default=user_input.get(CONF_EMAIL, "")): str,
                        vol.Optional(CONF_PASSWORD, default=""): str,
                    }
                ),
                errors=errors,
                description_placeholders={
                    "note": "Leave email and password empty for public data only (liquid types and schedules). Enter credentials for full device control."
                }
            )

        # Show initial form with current settings
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_EMAIL, default=entry.data.get(CONF_EMAIL, "")): str,
                    vol.Optional(CONF_PASSWORD, default=""): str,
                }
            ),
            description_placeholders={
                "note": "Leave email and password empty for public data only (liquid types and schedules). Enter credentials for full device control."
            }
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""