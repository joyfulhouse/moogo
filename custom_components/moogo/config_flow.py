"""Config flow for Moogo integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pymoogo import MoogoAPIError, MoogoAuthError, MoogoClient, MoogoRateLimitError

from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Error keys for config flow
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_AUTH = "invalid_auth"
ERROR_RATE_LIMITED = "rate_limited"
ERROR_RELOAD_FAILED = "reload_failed"
ERROR_UNKNOWN = "unknown"

# Basic config flow for email/password authentication or public data only
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_EMAIL, default=""): str,
        vol.Optional(CONF_PASSWORD, default=""): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Args:
        hass: Home Assistant instance.
        data: User input data with optional email and password.

    Returns:
        Dictionary containing the title for the config entry.

    Raises:
        CannotConnect: If API is unreachable.
        InvalidAuth: If credentials are invalid.
        RateLimited: If rate limited by API.
    """
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)

    client = MoogoClient(
        email=data.get(CONF_EMAIL),
        password=data.get(CONF_PASSWORD),
        session=session,
    )

    # Test public endpoints first (always works)
    try:
        await client.get_liquid_types()
    except MoogoAPIError as err:
        _LOGGER.error("Cannot connect to Moogo API: %s", err)
        raise CannotConnect from err

    # If credentials provided, test authentication
    if data.get(CONF_EMAIL) and data.get(CONF_PASSWORD):
        try:
            await client.authenticate()
        except MoogoRateLimitError as err:
            _LOGGER.error("Rate limited during authentication: %s", err)
            raise RateLimited from err
        except MoogoAuthError as err:
            _LOGGER.error("Invalid authentication: %s", err)
            raise InvalidAuth from err
        title = f"Moogo ({data[CONF_EMAIL]})"
    else:
        title = "Moogo (Public Data Only)"

    return {"title": title}


def _handle_validation_errors(err: Exception, context: str = "") -> dict[str, str]:
    """Handle validation errors and return appropriate error dictionary.

    Args:
        err: The exception that was raised.
        context: Additional context for logging (e.g., 'during reauth').

    Returns:
        Dictionary with error key for the form.
    """
    if isinstance(err, CannotConnect):
        return {"base": ERROR_CANNOT_CONNECT}
    if isinstance(err, InvalidAuth):
        return {"base": ERROR_INVALID_AUTH}
    if isinstance(err, RateLimited):
        return {"base": ERROR_RATE_LIMITED}

    _LOGGER.exception("Unexpected exception%s", f" {context}" if context else "")
    return {"base": ERROR_UNKNOWN}


async def _safe_reload_entry(
    hass: HomeAssistant, entry_id: str
) -> dict[str, str] | None:
    """Safely reload a config entry with error handling.

    Args:
        hass: Home Assistant instance.
        entry_id: ID of the config entry to reload.

    Returns:
        Error dictionary if reload failed, None if successful.
    """
    try:
        await hass.config_entries.async_reload(entry_id)
        return None
    except Exception as err:
        _LOGGER.error("Failed to reload config entry: %s", err)
        return {"base": ERROR_RELOAD_FAILED}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Moogo."""

    VERSION: int = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self._show_user_form()

        errors = await self._validate_user_input(user_input)
        if errors:
            return self._show_user_form(errors)

        # Set unique ID and prevent duplicates
        if user_input.get(CONF_EMAIL) and user_input.get(CONF_PASSWORD):
            await self.async_set_unique_id(user_input[CONF_EMAIL])
        else:
            await self.async_set_unique_id("public_data")
        self._abort_if_unique_id_configured()

        info = await validate_input(self.hass, user_input)
        return self.async_create_entry(title=info["title"], data=user_input)

    def _show_user_form(self, errors: dict[str, str] | None = None) -> ConfigFlowResult:
        """Show the user configuration form.

        Args:
            errors: Optional error dictionary to display.

        Returns:
            ConfigFlowResult showing the form.
        """
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors or {},
            description_placeholders={
                "note": "Leave email and password empty for public data only "
                "(liquid types and schedules). Enter credentials for full device control."
            },
        )

    async def _validate_user_input(
        self, user_input: dict[str, Any]
    ) -> dict[str, str] | None:
        """Validate user input and return errors if any.

        Args:
            user_input: User provided configuration data.

        Returns:
            Error dictionary if validation failed, None if successful.
        """
        try:
            await validate_input(self.hass, user_input)
            return None
        except (CannotConnect, InvalidAuth, RateLimited, Exception) as err:
            return _handle_validation_errors(err)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauthentication when credentials expire or fail."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        self.entry: ConfigEntry = entry
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthentication confirmation."""
        if user_input is None:
            return self._show_reauth_form()

        # Get credentials from input
        email = user_input.get(CONF_EMAIL) or self.entry.data.get(CONF_EMAIL)
        password = user_input.get(CONF_PASSWORD)

        if not email or not password:
            return self._show_reauth_form({ERROR_INVALID_AUTH: ERROR_INVALID_AUTH})

        # Validate credentials
        validation_data = {CONF_EMAIL: email, CONF_PASSWORD: password}

        try:
            await validate_input(self.hass, validation_data)
        except (CannotConnect, InvalidAuth, RateLimited, Exception) as err:
            return self._show_reauth_form(
                _handle_validation_errors(err, "during reauth")
            )

        # Update config entry with new credentials
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={**self.entry.data, CONF_EMAIL: email, CONF_PASSWORD: password},
        )

        # Reload config entry
        reload_error = await _safe_reload_entry(self.hass, self.entry.entry_id)
        if reload_error:
            return self._show_reauth_form(reload_error)

        return self.async_abort(reason="reauth_successful")

    def _show_reauth_form(
        self, errors: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Show the reauthentication form.

        Args:
            errors: Optional error dictionary to display.

        Returns:
            ConfigFlowResult showing the form.
        """
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL, default=self.entry.data.get(CONF_EMAIL, "")
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors or {},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None

        if user_input is None:
            return self._show_reconfigure_form(entry)

        # Validate new configuration
        try:
            info = await validate_input(self.hass, user_input)
        except (CannotConnect, InvalidAuth, RateLimited, Exception) as err:
            return self._show_reconfigure_form(
                entry,
                _handle_validation_errors(err, "during reconfiguration"),
                user_input,
            )

        # Update config entry
        self.hass.config_entries.async_update_entry(
            entry, data=user_input, title=info["title"]
        )

        # Reload config entry
        reload_error = await _safe_reload_entry(self.hass, entry.entry_id)
        if reload_error:
            return self._show_reconfigure_form(entry, reload_error, user_input)

        return self.async_abort(reason="reconfigure_successful")

    def _show_reconfigure_form(
        self,
        entry: ConfigEntry,
        errors: dict[str, str] | None = None,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show the reconfiguration form.

        Args:
            entry: Current config entry.
            errors: Optional error dictionary to display.
            user_input: Previously entered user input for defaults.

        Returns:
            ConfigFlowResult showing the form.
        """
        # Use user_input for defaults if available, otherwise use entry data
        defaults = user_input or entry.data

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")): str,
                    vol.Optional(CONF_PASSWORD, default=""): str,
                }
            ),
            errors=errors or {},
            description_placeholders={
                "note": "Leave email and password empty for public data only "
                "(liquid types and schedules). Enter credentials for full device control."
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class RateLimited(HomeAssistantError):
    """Error to indicate rate limiting."""
