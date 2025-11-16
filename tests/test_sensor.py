"""Test the Moogo sensor platform."""

from __future__ import annotations


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from custom_components.moogo.const import DOMAIN
from custom_components.moogo.sensor import async_setup_entry


async def test_sensor_setup_public_only(hass: HomeAssistant, mock_moogo_client) -> None:
    """Test sensor setup with public data only."""
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
        "liquid_types": [{"liquidName": "Type 1"}],
        "recommended_schedules": [{"title": "Schedule 1"}],
        "devices": [],
    }
    mock_coordinator.last_update_success = True
    config_entry.runtime_data = mock_coordinator

    entities = []

    async def mock_add_entities(new_entities, update_before_add=True):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)

    # Should have 3 public data sensors only
    assert len(entities) == 3
    assert any("Liquid Types" in e._attr_name for e in entities)
    assert any("Schedule Templates" in e._attr_name for e in entities)
    assert any("API Status" in e._attr_name for e in entities)


async def test_sensor_setup_authenticated(
    hass: HomeAssistant, mock_moogo_client
) -> None:
    """Test sensor setup with authentication."""
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
        "liquid_types": [{"liquidName": "Type 1"}],
        "recommended_schedules": [{"title": "Schedule 1"}],
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
                "temperature": 25.5,
                "humidity": 60,
                "rssi": -45,
                "liquid_level": 1,
                "water_level": 1,
            }
        },
        "device_schedules": {"device_1": {"items": []}},
    }
    mock_coordinator.last_update_success = True
    config_entry.runtime_data = mock_coordinator

    entities = []

    async def mock_add_entities(new_entities, update_before_add=True):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)

    # Should have 3 public sensors + 8 device sensors = 11 total
    assert len(entities) == 11


async def test_sensor_has_entity_name(hass: HomeAssistant, mock_moogo_client) -> None:
    """Test that sensors have entity name attribute set."""
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
        "liquid_types": [],
        "recommended_schedules": [],
        "devices": [],
    }
    mock_coordinator.last_update_success = True
    config_entry.runtime_data = mock_coordinator

    entities = []

    async def mock_add_entities(new_entities, update_before_add=True):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)

    # All sensors should have has_entity_name set to True
    for entity in entities:
        assert entity._attr_has_entity_name is True
