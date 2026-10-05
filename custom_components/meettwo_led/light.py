"""Light platform for MeetTwo LED."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from .const import ATTR_COLORS, ATTR_SPEED, SERVICE_SET_EFFECT
from .coordinator import MeetTwoConfigEntry, MeetTwoCoordinator
from .entity import AddEntitiesCallback, MeetTwoEntity
from .services import REGISTER_IN_PLATFORM, SET_EFFECT_SCHEMA

try:
    from homeassistant.components.light import EFFECT_OFF
except ImportError:  # older Home Assistant
    EFFECT_OFF = "off"

API_EFFECT_NONE = "none"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeetTwoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light."""
    async_add_entities([MeetTwoLight(entry.runtime_data)])

    if REGISTER_IN_PLATFORM:
        entity_platform.async_get_current_platform().async_register_entity_service(
            SERVICE_SET_EFFECT, SET_EFFECT_SCHEMA, "async_set_effect"
        )


def _to_api_brightness(ha_brightness: int) -> int:
    """HA 1..255 -> API 0..100 %; never 0 for a light that should be on."""
    return max(1, min(100, round(ha_brightness * 100 / 255)))


class MeetTwoLight(MeetTwoEntity, LightEntity):
    """The LED border."""

    _attr_name = None  # use the device name
    _attr_translation_key = "led_border"
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(self, coordinator: MeetTwoCoordinator) -> None:
        super().__init__(coordinator, "light")

    @property
    def _state(self) -> dict[str, Any]:
        return self.coordinator.data

    @property
    def is_on(self) -> bool:
        return bool(self._state.get("power"))

    @property
    def brightness(self) -> int:
        return round(int(self._state.get("brightness", 100)) * 255 / 100)

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        rgb = self._state.get("rgb") or {}
        return (int(rgb.get("r", 255)), int(rgb.get("g", 255)), int(rgb.get("b", 255)))

    @property
    def effect_list(self) -> list[str]:
        return [EFFECT_OFF, *(e for e in self.coordinator.effects if e != API_EFFECT_NONE)]

    @property
    def effect(self) -> str | None:
        effect = self._state.get("effect", API_EFFECT_NONE)
        return EFFECT_OFF if effect == API_EFFECT_NONE else effect

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            ATTR_SPEED: self._state.get("speed"),
            ATTR_COLORS: self._state.get("colors"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        params: dict[str, Any] = {"power": "on"}
        if ATTR_BRIGHTNESS in kwargs:
            params["brightness"] = _to_api_brightness(kwargs[ATTR_BRIGHTNESS])
        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            params["color"] = f"{r},{g},{b}"
        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            params["effect"] = API_EFFECT_NONE if effect == EFFECT_OFF else effect
        await self.coordinator.async_send(**params)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send(power="off")

    async def async_set_effect(
        self,
        effect: str,
        color: str | None = None,
        colors: list[str] | None = None,
        speed: int | None = None,
        brightness_pct: int | None = None,
    ) -> None:
        """Handle the meettwo_led.set_effect action."""
        params: dict[str, Any] = {
            "effect": API_EFFECT_NONE if effect == EFFECT_OFF else effect,
        }
        if color is not None:
            params["color"] = color
        if colors:
            params["colors"] = colors
        if speed is not None:
            params["speed"] = speed
        if brightness_pct is not None:
            params["brightness"] = brightness_pct
        await self.coordinator.async_send(**params)