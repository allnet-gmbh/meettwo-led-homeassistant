"""Diagnostic sensors for MeetTwo LED."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .coordinator import MeetTwoConfigEntry, MeetTwoCoordinator
from .entity import AddEntitiesCallback, MeetTwoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeetTwoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    async_add_entities([MeetTwoLastError(entry.runtime_data)])


class MeetTwoLastError(MeetTwoEntity, SensorEntity):
    """Last hardware error reported by the device (empty if none)."""

    _attr_translation_key = "last_error"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MeetTwoCoordinator) -> None:
        super().__init__(coordinator, "last_error")

    @property
    def native_value(self) -> str:
        # HA state strings are limited to 255 characters
        return (self.coordinator.data.get("lastError") or "")[:255]