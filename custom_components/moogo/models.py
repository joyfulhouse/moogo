"""Data models and type definitions for the Moogo integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict


class DeviceData(TypedDict):
    """Device data structure from coordinator."""

    deviceId: str
    deviceName: str
    model: str


class CoordinatorData(TypedDict, total=False):
    """Data structure returned by the coordinator.

    Attributes:
        liquid_types: List of available liquid concentrate types.
        recommended_schedules: List of recommended spray schedules.
        devices: List of device data dictionaries.
        auth_status: Authentication status ('authenticated' or 'public_only').
        update_time: Timestamp of last successful update.
    """

    liquid_types: list[dict[str, Any]]
    recommended_schedules: list[dict[str, Any]]
    devices: list[DeviceData]
    auth_status: str
    update_time: datetime | None


class LiquidType(TypedDict, total=False):
    """Liquid type data from API."""

    id: str
    liquidName: str
    description: str


class ScheduleTemplate(TypedDict, total=False):
    """Schedule template data from API."""

    id: str
    title: str
    hour: int
    minute: int


class ScheduleInfo(TypedDict):
    """Formatted schedule information for attributes."""

    id: str | None
    time: str
    duration: int
    repeat: str
    status: str


class ScheduleCache(TypedDict):
    """Cached schedule data structure."""

    id: str
    hour: int
    minute: int
    duration: int
    repeatSet: str
    status: int
