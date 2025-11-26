"""Base entity classes and mixins for the Moogo integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pymoogo import MoogoDevice

from .const import DEFAULT_MANUFACTURER, DEFAULT_MODEL, DOMAIN

if TYPE_CHECKING:
    from .coordinator import MoogoCoordinator

_LOGGER = logging.getLogger(__name__)


class MoogoCoordinatorEntity(CoordinatorEntity["MoogoCoordinator"]):
    """Base class for Moogo entities using the coordinator.

    Provides common availability tracking with logging.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: MoogoCoordinator) -> None:
        """Initialize the entity.

        Args:
            coordinator: The Moogo data update coordinator.
        """
        super().__init__(coordinator)
        self._was_available: bool | None = None

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Logs availability changes for debugging.
        """
        is_available = bool(self.coordinator.last_update_success)
        self._log_availability_change(is_available, "coordinator update failed")
        return is_available

    def _log_availability_change(
        self,
        is_available: bool,
        unavailable_reason: str = "unknown",
    ) -> None:
        """Log availability state changes.

        Args:
            is_available: Current availability state.
            unavailable_reason: Reason for unavailability (used in warning log).
        """
        if self._was_available is not None and self._was_available != is_available:
            if is_available:
                _LOGGER.debug("%s is now available", self.name)
            else:
                _LOGGER.warning(
                    "%s is now unavailable (%s)",
                    self.name,
                    unavailable_reason,
                )
        self._was_available = is_available


class MoogoDeviceEntity(MoogoCoordinatorEntity):
    """Base class for device-specific Moogo entities.

    Provides device lookup, device_info, and availability tracking
    specific to individual devices.
    """

    def __init__(
        self,
        coordinator: MoogoCoordinator,
        device_id: str,
        device_name: str,
    ) -> None:
        """Initialize the device entity.

        Args:
            coordinator: The Moogo data update coordinator.
            device_id: Unique device identifier.
            device_name: Human-readable device name.
        """
        super().__init__(coordinator)
        self.device_id = device_id
        self.device_name = device_name

    @property
    def device(self) -> MoogoDevice | None:
        """Get the MoogoDevice instance from coordinator."""
        return self.coordinator.get_device(self.device_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the device registry."""
        device = self.device
        info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self.device_name,
            manufacturer=DEFAULT_MANUFACTURER,
            model=DEFAULT_MODEL,
        )
        if device and device.firmware:
            info["sw_version"] = device.firmware
        return info

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Entity is available when:
        - Device exists in coordinator
        - Coordinator last update was successful
        """
        device = self.device
        is_available = device is not None and self.coordinator.last_update_success

        # Determine reason for unavailability
        if not is_available:
            if not self.coordinator.last_update_success:
                reason = "coordinator update failed"
            elif device is None:
                reason = "device not found"
            else:
                reason = "unknown"
        else:
            reason = ""

        self._log_availability_change(is_available, reason)
        return is_available


class MoogoDeviceControlEntity(MoogoDeviceEntity):
    """Base class for device control entities (switches, buttons).

    Extends availability check to also require:
    - Device to be online
    - API to be authenticated
    """

    @property
    def available(self) -> bool:
        """Return if control entity is available.

        Control entities require:
        - Device exists in coordinator
        - Coordinator last update was successful
        - Device is online
        - Client is authenticated
        """
        device = self.device
        is_available = False

        if device and self.coordinator.client.is_authenticated:
            is_available = device.is_online and self.coordinator.last_update_success

        # Determine reason for unavailability
        if not is_available:
            if not self.coordinator.client.is_authenticated:
                reason = "API not authenticated"
            elif not self.coordinator.last_update_success:
                reason = "coordinator update failed"
            elif device is None:
                reason = "device not found"
            elif not device.is_online:
                reason = "device offline"
            else:
                reason = "unknown"
        else:
            reason = ""

        self._log_availability_change(is_available, reason)
        return is_available
