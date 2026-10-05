"""Constants for the MeetTwo LED integration."""

from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "meettwo_led"
LOGGER = logging.getLogger(__package__)

MANUFACTURER: Final = "ALLNET"
MODEL: Final = "MeetTwo LED border"

DEFAULT_PORT: Final = 8080
DEFAULT_NAME: Final = "MeetTwo LED"

CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL: Final = 10  # seconds
MIN_SCAN_INTERVAL: Final = 2
MAX_SCAN_INTERVAL: Final = 300

# API limits (see API.md of the Android app)
SUPPORTED_API_VERSION: Final = 1
MIN_SPEED: Final = 50
MAX_SPEED: Final = 600_000

SERVICE_SET_EFFECT: Final = "set_effect"
ATTR_COLORS: Final = "colors"
ATTR_SPEED: Final = "speed"
ATTR_COLOR: Final = "color"