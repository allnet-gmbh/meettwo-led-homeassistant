"""Base entity for MeetTwo LED."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import MeetTwoCoordinator

try:  # Home Assistant >= 2025.2
    from homeassistant.helpers.entity_platform import (
        AddConfigEntryEntitiesCallback as AddEntitiesCallback,
    )
except ImportError:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback  # noqa: F401


class MeetTwoEntity(CoordinatorEntity[MeetTwoCoordinator]):
    """Common device info and unique id handling."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MeetTwoCoordinator, key: str) -> None:
        super().__init__(coordinator)
        info = coordinator.device_info_raw
        self._attr_unique_id = f"{coordinator.device_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name=coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            hw_version=info.get("model"),
            sw_version=info.get("appVersion"),
            configuration_url=f"{coordinator.api.base_url}/",
        )