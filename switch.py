"""Switch platform for Moogo integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MoogoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Moogo switch entities."""
    coordinator: MoogoCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Only add switch entities if authenticated and devices found
    if coordinator.api.is_authenticated and coordinator.data.get("devices"):
        for device in coordinator.data["devices"]:
            device_id = device.get("deviceId")
            device_name = device.get("deviceName", f"Moogo Device {device_id}")
            
            if device_id:
                entities.append(MoogoSpraySwitch(coordinator, device_id, device_name))
    
    if entities:
        async_add_entities(entities, update_before_add=True)


class MoogoSpraySwitch(CoordinatorEntity, SwitchEntity):
    """Switch entity for controlling spray functionality."""

    def __init__(self, coordinator: MoogoCoordinator, device_id: str, device_name: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.device_id = device_id
        self.device_name = device_name
        
        self._attr_name = f"{device_name} Spray"
        self._attr_unique_id = f"{device_id}_spray_switch"
        self._attr_icon = "mdi:spray"

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.device_name,
            "manufacturer": "Moogo",
            "model": "Smart Spray Device",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        # Check if device is online and API is authenticated
        if device_status and self.coordinator.api.is_authenticated:
            online_status = device_status.get("onlineStatus", 0)
            return online_status == 1 and self.coordinator.last_update_success
        return False

    @property
    def is_on(self) -> bool | None:
        """Return true if the spray is currently running."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status:
            run_status = device_status.get("runStatus", 0)
            return run_status == 1  # 1 = running, 0 = stopped
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the spray with polling to verify start."""
        try:
            # Default spray duration of 60 seconds, can be customized
            duration = kwargs.get("duration", 60)
            
            _LOGGER.info(f"Starting spray for device {self.device_id} with duration {duration}s")
            
            # Send the start spray command
            success = await self.coordinator.api.start_spray(self.device_id, duration)
            
            if not success:
                _LOGGER.error(f"API call failed to start spray for {self.device_name}")
                return
            
            _LOGGER.info(f"Start spray command sent for {self.device_name}, now polling for status confirmation...")
            
            # Poll the device status every 5 seconds to wait for it to come online and start spraying
            # The API exhibits strange behavior where it reports offline initially
            poll_attempts = 0
            max_poll_attempts = 12  # Poll for up to 60 seconds (12 * 5 seconds)
            spray_confirmed = False
            
            while poll_attempts < max_poll_attempts and not spray_confirmed:
                poll_attempts += 1
                
                # Wait 5 seconds before polling
                await asyncio.sleep(5)
                
                _LOGGER.debug(f"Polling attempt {poll_attempts}/{max_poll_attempts} for {self.device_name}")
                
                # Refresh device status
                device_status = await self.coordinator.api.get_device_status(self.device_id)
                
                if device_status:
                    online_status = device_status.get("onlineStatus", 0)
                    run_status = device_status.get("runStatus", 0)
                    
                    _LOGGER.debug(f"Device {self.device_id} status - Online: {online_status}, Running: {run_status}")
                    
                    # Check if device is online and spraying
                    if online_status == 1 and run_status == 1:
                        spray_confirmed = True
                        _LOGGER.info(f"✅ Spray successfully started for {self.device_name} (confirmed after {poll_attempts * 5}s)")
                        break
                    elif online_status == 1 and run_status == 0:
                        _LOGGER.warning(f"Device {self.device_name} is online but not spraying after {poll_attempts * 5}s")
                    else:
                        _LOGGER.debug(f"Device {self.device_name} still offline, continuing to poll...")
                else:
                    _LOGGER.warning(f"Failed to get device status for {self.device_name} on poll attempt {poll_attempts}")
            
            if not spray_confirmed:
                _LOGGER.warning(f"⚠️ Spray command sent but could not confirm spray started for {self.device_name} after {max_poll_attempts * 5}s")
            
            # Refresh coordinator data to reflect the final state
            await self.coordinator.async_request_refresh()
                
        except Exception as e:
            _LOGGER.error(f"Error starting spray for {self.device_name}: {e}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the spray with polling to verify stop."""
        try:
            _LOGGER.info(f"Stopping spray for device {self.device_id}")
            success = await self.coordinator.api.stop_spray(self.device_id, "manual_stop")
            
            if not success:
                _LOGGER.error(f"API call failed to stop spray for {self.device_name}")
                return
            
            _LOGGER.info(f"Stop spray command sent for {self.device_name}, polling for confirmation...")
            
            # Poll the device status to confirm spray has stopped
            poll_attempts = 0
            max_poll_attempts = 6  # Poll for up to 30 seconds (6 * 5 seconds)
            stop_confirmed = False
            
            while poll_attempts < max_poll_attempts and not stop_confirmed:
                poll_attempts += 1
                
                # Wait 5 seconds before polling
                await asyncio.sleep(5)
                
                _LOGGER.debug(f"Stop polling attempt {poll_attempts}/{max_poll_attempts} for {self.device_name}")
                
                # Refresh device status
                device_status = await self.coordinator.api.get_device_status(self.device_id)
                
                if device_status:
                    run_status = device_status.get("runStatus", 0)
                    online_status = device_status.get("onlineStatus", 0)
                    
                    _LOGGER.debug(f"Device {self.device_id} status - Online: {online_status}, Running: {run_status}")
                    
                    # Check if device has stopped spraying
                    if run_status == 0:
                        stop_confirmed = True
                        _LOGGER.info(f"✅ Spray successfully stopped for {self.device_name} (confirmed after {poll_attempts * 5}s)")
                        break
                    else:
                        _LOGGER.debug(f"Device {self.device_name} still spraying, continuing to poll...")
                else:
                    _LOGGER.warning(f"Failed to get device status for {self.device_name} on stop poll attempt {poll_attempts}")
            
            if not stop_confirmed:
                _LOGGER.warning(f"⚠️ Stop command sent but could not confirm spray stopped for {self.device_name} after {max_poll_attempts * 5}s")
            
            # Refresh coordinator data to reflect the final state
            await self.coordinator.async_request_refresh()
                
        except Exception as e:
            _LOGGER.error(f"Error stopping spray for {self.device_name}: {e}")

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        """Return additional state attributes."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status:
            return {
                "device_id": self.device_id,
                "run_status": device_status.get("runStatus", 0),
                "online_status": device_status.get("onlineStatus", 0),
                "latest_spraying_duration": device_status.get("latestSprayingDuration", 0),
                "liquid_level": device_status.get("liquid_level", 0),
                "water_level": device_status.get("water_level", 0),
            }
        return {}