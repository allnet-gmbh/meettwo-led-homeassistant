"""Data update coordinator for MeetTwo LED."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MeetTwoApi, MeetTwoAuthError, MeetTwoConnectionError, MeetTwoError
from .const import CONF_SCAN_INTERVAL, DEFAULT_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER

type MeetTwoConfigEntry = ConfigEntry[MeetTwoCoordinator]


class MeetTwoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls /api/status and sends commands."""

    config_entry: MeetTwoConfigEntry

    def __init__(self, hass: HomeAssistant, entry: MeetTwoConfigEntry, api: MeetTwoApi) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.api = api
        self.device_info_raw: dict[str, Any] = {}
        self.effects: list[str] = []

    @property
    def device_id(self) -> str:
        """Stable device id (config entry unique id)."""
        return self.config_entry.unique_id or self.config_entry.entry_id

    @property
    def device_name(self) -> str:
        """Name configured in the app."""
        return self.device_info_raw.get("deviceName") or self.config_entry.title or DEFAULT_NAME

    async def _async_setup(self) -> None:
        """Load static device info once."""
        try:
            self.device_info_raw = await self.api.help()
            self.effects = list((await self.api.effects()).keys())
        except MeetTwoAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MeetTwoError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.status()
        except MeetTwoAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MeetTwoConnectionError as err:
            raise UpdateFailed(f"Device not reachable: {err}") from err
        except MeetTwoError as err:
            raise UpdateFailed(str(err)) from err

    async def async_send(self, **params: Any) -> None:
        """Send a command and update all entities with the returned state."""
        try:
            state = await self.api.set(**params)
        except MeetTwoAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(f"Authentication failed: {err}") from err
        except MeetTwoError as err:
            raise HomeAssistantError(f"MeetTwo LED command failed: {err}") from err
        self.async_set_updated_data(state)