"""Actions (services) for MeetTwo LED."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.light import ATTR_EFFECT, DOMAIN as LIGHT_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from .const import ATTR_COLOR, ATTR_COLORS, ATTR_SPEED, DOMAIN, MAX_SPEED, MIN_SPEED, SERVICE_SET_EFFECT

ATTR_BRIGHTNESS_PCT = "brightness_pct"

SET_EFFECT_SCHEMA = {
    vol.Required(ATTR_EFFECT): cv.string,
    vol.Optional(ATTR_COLOR): cv.string,
    vol.Optional(ATTR_COLORS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_SPEED): vol.All(vol.Coerce(int), vol.Range(min=MIN_SPEED, max=MAX_SPEED)),
    vol.Optional(ATTR_BRIGHTNESS_PCT): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
}

try:  # Home Assistant >= 2025.x: register once in async_setup
    from homeassistant.helpers.service import async_register_platform_entity_service

    REGISTER_IN_PLATFORM = False
except ImportError:  # older versions: register when the light platform is set up
    async_register_platform_entity_service = None
    REGISTER_IN_PLATFORM = True


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration actions."""
    if async_register_platform_entity_service is None:
        return
    async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_SET_EFFECT,
        entity_domain=LIGHT_DOMAIN,
        schema=SET_EFFECT_SCHEMA,
        func="async_set_effect",
    )