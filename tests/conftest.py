"""Fixtures for MeetTwo LED tests."""

from __future__ import annotations

from collections.abc import Generator
import copy
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meettwo_led.const import DOMAIN

DEVICE_ID = "7604a94aeb17"

HELP = {
    "name": "MeetTwo LED API",
    "apiVersion": 1,
    "deviceId": DEVICE_ID,
    "deviceName": "Meeting Room",
    "model": "rk3576",
    "appVersion": "1.0",
    "passwordRequired": False,
}

STATE = {
    "power": True,
    "color": "#FF8800",
    "colorName": None,
    "rgb": {"r": 255, "g": 136, "b": 0},
    "brightness": 50,
    "effect": "none",
    "speed": 2000,
    "colors": ["#FF0000", "#00FF00", "#0000FF"],
    "hardwareAvailable": True,
    "hardwareLevels": {"r": 8, "g": 4, "b": 0},
    "lastError": None,
}

EFFECTS = {
    "none": "Static color",
    "blink": "...",
    "strobe": "...",
    "breathe": "...",
    "rainbow": "...",
    "cycle": "...",
    "fade": "...",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom_components in all tests."""


@pytest.fixture
def mock_api() -> Generator[dict[str, AsyncMock]]:
    """Patch all API calls. `set` echoes the params into the state like the device does."""
    state = copy.deepcopy(STATE)

    async def _set(self: Any, **params: Any) -> dict[str, Any]:
        if "power" in params:
            state["power"] = params["power"] == "on"
        if "brightness" in params:
            state["brightness"] = params["brightness"]
        if "effect" in params:
            state["effect"] = params["effect"]
            state["power"] = True
        if "speed" in params:
            state["speed"] = params["speed"]
        return copy.deepcopy(state)

    async def _status(self: Any) -> dict[str, Any]:
        return copy.deepcopy(state)

    with (
        patch("custom_components.meettwo_led.api.MeetTwoApi.help", autospec=True, return_value=HELP) as help_,
        patch("custom_components.meettwo_led.api.MeetTwoApi.status", autospec=True, side_effect=_status) as status,
        patch("custom_components.meettwo_led.api.MeetTwoApi.effects", autospec=True, return_value=EFFECTS) as effects,
        patch("custom_components.meettwo_led.api.MeetTwoApi.set", autospec=True, side_effect=_set) as set_,
    ):
        yield {"help": help_, "status": status, "effects": effects, "set": set_, "state": state}


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A configured device."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Meeting Room",
        unique_id=DEVICE_ID,
        data={CONF_HOST: "10.0.0.5", CONF_PORT: 8080},
    )