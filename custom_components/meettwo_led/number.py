"""Number platform (effect speed) for MeetTwo LED."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant

from .const import MAX_SPEED, MIN_SPEED
from .coordinator import MeetTwoConfigEntry, MeetTwoCoordinator
from .entity import AddEntitiesCallback, MeetTwoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeetTwoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number entities."""
    async_add_entities([MeetTwoEffectSpeed(entry.runtime_data)])


class MeetTwoEffectSpeed(MeetTwoEntity, NumberEntity):
    """Effect speed in milliseconds (period / time per color, depending on the effect)."""

    _attr_translation_key = "effect_speed"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    _attr_native_min_value = MIN_SPEED
    _attr_native_max_value = MAX_SPEED
    _attr_native_step = 50
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: MeetTwoCoordinator) -> None:
        super().__init__(coordinator, "effect_speed")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("speed")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_send(speed=int(value))