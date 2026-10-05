"""Entity tests."""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock

import pytest

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_RGB_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.components.number import ATTR_VALUE, DOMAIN as NUMBER_DOMAIN, SERVICE_SET_VALUE
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meettwo_led.api import MeetTwoError
from custom_components.meettwo_led.const import DOMAIN

LIGHT = "light.meeting_room"
SPEED = "number.meeting_room_effect_speed"
PROBLEM = "binary_sensor.meeting_room_led_hardware"
LAST_ERROR = "sensor.meeting_room_last_error"


@pytest.fixture
async def setup(hass: HomeAssistant, mock_api: dict[str, AsyncMock], config_entry: MockConfigEntry) -> dict:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    return mock_api


async def test_light_state(hass: HomeAssistant, setup: dict) -> None:
    state = hass.states.get(LIGHT)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 128  # 50 %
    assert state.attributes[ATTR_RGB_COLOR] == (255, 136, 0)
    assert state.attributes[ATTR_EFFECT] == "off"
    assert state.attributes[ATTR_EFFECT_LIST] == ["off", "blink", "strobe", "breathe", "rainbow", "cycle", "fade"]


async def test_turn_on_with_color_and_brightness(hass: HomeAssistant, setup: dict) -> None:
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: LIGHT, ATTR_BRIGHTNESS: 255, ATTR_RGB_COLOR: (0, 0, 255)},
        blocking=True,
    )
    setup["set"].assert_called_with(ANY, power="on", brightness=100, color="0,0,255")


async def test_low_brightness_never_zero(hass: HomeAssistant, setup: dict) -> None:
    await hass.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: LIGHT, ATTR_BRIGHTNESS: 1}, blocking=True
    )
    setup["set"].assert_called_with(ANY, power="on", brightness=1)


async def test_effects(hass: HomeAssistant, setup: dict) -> None:
    await hass.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: LIGHT, ATTR_EFFECT: "rainbow"}, blocking=True
    )
    setup["set"].assert_called_with(ANY, power="on", effect="rainbow")
    assert hass.states.get(LIGHT).attributes[ATTR_EFFECT] == "rainbow"

    await hass.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: LIGHT, ATTR_EFFECT: "off"}, blocking=True
    )
    setup["set"].assert_called_with(ANY, power="on", effect="none")


async def test_turn_off(hass: HomeAssistant, setup: dict) -> None:
    await hass.services.async_call(LIGHT_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: LIGHT}, blocking=True)
    setup["set"].assert_called_with(ANY, power="off")
    assert hass.states.get(LIGHT).state == STATE_OFF


async def test_set_effect_action(hass: HomeAssistant, setup: dict) -> None:
    await hass.services.async_call(
        DOMAIN,
        "set_effect",
        {ATTR_ENTITY_ID: LIGHT, "effect": "fade", "colors": ["red", "#00FF00"], "speed": 1500, "brightness_pct": 70},
        blocking=True,
    )
    setup["set"].assert_called_with(ANY, effect="fade", colors=["red", "#00FF00"], speed=1500, brightness=70)


async def test_command_error(hass: HomeAssistant, setup: dict) -> None:
    setup["set"].side_effect = MeetTwoError("Hardware write failed")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(LIGHT_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: LIGHT}, blocking=True)


async def test_speed_number(hass: HomeAssistant, setup: dict) -> None:
    assert hass.states.get(SPEED).state == "2000"
    await hass.services.async_call(
        NUMBER_DOMAIN, SERVICE_SET_VALUE, {ATTR_ENTITY_ID: SPEED, ATTR_VALUE: 500}, blocking=True
    )
    setup["set"].assert_called_with(ANY, speed=500)
    assert hass.states.get(SPEED).state == "500"


async def test_diagnostic_entities(hass: HomeAssistant, setup: dict) -> None:
    assert hass.states.get(PROBLEM).state == STATE_OFF
    assert hass.states.get(LAST_ERROR).state == ""


async def test_unload(hass: HomeAssistant, setup: dict, config_entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED