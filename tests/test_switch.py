"""Test the Moogo switch platform."""

from __future__ import annotations


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from custom_components.moogo.const import DOMAIN
from custom_components.moogo.switch import async_setup_entry


async def test_switch_setup_authenticated(
    hass: HomeAssistant, mock_moogo_client
) -> None:
    """Test switch setup with authentication."""
    config_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (test@example.com)",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        entry_id="test_entry_id",
        unique_id="test@example.com",
    )

    mock_coordinator = MagicMock()
    mock_coordinator.api = mock_moogo_client
    mock_coordinator.data = {
        "devices": [
            {
                "deviceId": "device_1",
                "deviceName": "Test Device 1",
            }
        ],
        "device_statuses": {
            "device_1": {
                "onlineStatus": 1,
                "runStatus": 0,
            }
        },
    }
    mock_coordinator.last_update_success = True
    mock_coordinator.async_request_refresh = AsyncMock()
    config_entry.runtime_data = mock_coordinator

    entities = []

    async def mock_add_entities(new_entities, update_before_add=True):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)

    # Should have 1 switch per device
    assert len(entities) == 1
    assert entities[0]._attr_has_entity_name is True


async def test_switch_setup_public_only(hass: HomeAssistant, mock_moogo_client) -> None:
    """Test switch setup with public data only (no switches created)."""
    mock_moogo_client.is_authenticated = False

    config_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (Public Data Only)",
        data={},
        source="user",
        entry_id="test_entry_id",
        unique_id="public_data",
    )

    mock_coordinator = MagicMock()
    mock_coordinator.api = mock_moogo_client
    mock_coordinator.data = {
        "devices": [],
    }
    config_entry.runtime_data = mock_coordinator

    entities = []

    async def mock_add_entities(new_entities, update_before_add=True):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)

    # Should have no switches for public data only
    assert len(entities) == 0


async def test_switch_turn_on(hass: HomeAssistant, mock_moogo_client) -> None:
    """Test switch turn on."""
    config_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (test@example.com)",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        entry_id="test_entry_id",
        unique_id="test@example.com",
    )

    mock_coordinator = MagicMock()
    mock_coordinator.api = mock_moogo_client
    mock_coordinator.data = {
        "devices": [{"deviceId": "device_1", "deviceName": "Test Device 1"}],
        "device_statuses": {"device_1": {"onlineStatus": 1, "runStatus": 0}},
    }
    mock_coordinator.last_update_success = True
    mock_coordinator.async_request_refresh = AsyncMock()
    config_entry.runtime_data = mock_coordinator

    # Mock start_spray to return success
    mock_moogo_client.start_spray = AsyncMock(return_value=True)
    mock_moogo_client.get_device_status = AsyncMock(
        return_value={"onlineStatus": 1, "runStatus": 1}
    )

    entities = []

    async def mock_add_entities(new_entities, update_before_add=True):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)

    # Turn on the switch
    switch = entities[0]
    await switch.async_turn_on()

    # Verify start_spray was called
    mock_moogo_client.start_spray.assert_called_once()


async def test_switch_turn_off(hass: HomeAssistant, mock_moogo_client) -> None:
    """Test switch turn off."""
    config_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (test@example.com)",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        entry_id="test_entry_id",
        unique_id="test@example.com",
    )

    mock_coordinator = MagicMock()
    mock_coordinator.api = mock_moogo_client
    mock_coordinator.data = {
        "devices": [{"deviceId": "device_1", "deviceName": "Test Device 1"}],
        "device_statuses": {"device_1": {"onlineStatus": 1, "runStatus": 1}},
    }
    mock_coordinator.last_update_success = True
    mock_coordinator.async_request_refresh = AsyncMock()
    config_entry.runtime_data = mock_coordinator

    # Mock stop_spray to return success
    mock_moogo_client.stop_spray = AsyncMock(return_value=True)
    mock_moogo_client.get_device_status = AsyncMock(
        return_value={"onlineStatus": 1, "runStatus": 0}
    )

    entities = []

    async def mock_add_entities(new_entities, update_before_add=True):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)

    # Turn off the switch
    switch = entities[0]
    await switch.async_turn_off()

    # Verify stop_spray was called
    mock_moogo_client.stop_spray.assert_called_once()
