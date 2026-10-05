"""Diagnostic binary sensor for MeetTwo LED."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .coordinator import MeetTwoConfigEntry, MeetTwoCoordinator
from .entity import AddEntitiesCallback, MeetTwoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeetTwoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    async_add_entities([MeetTwoHardwareProblem(entry.runtime_data)])


class MeetTwoHardwareProblem(MeetTwoEntity, BinarySensorEntity):
    """On when the LED hardware is unavailable or the last write failed."""

    _attr_translation_key = "hardware_problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MeetTwoCoordinator) -> None:
        super().__init__(coordinator, "hardware_problem")

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        return not data.get("hardwareAvailable", True) or bool(data.get("lastError"))