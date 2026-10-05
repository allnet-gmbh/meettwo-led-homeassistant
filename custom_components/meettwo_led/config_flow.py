"""Config flow for MeetTwo LED."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import MeetTwoApi, MeetTwoAuthError, MeetTwoConnectionError, MeetTwoError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SUPPORTED_API_VERSION,
)

try:
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
except ImportError:  # Home Assistant < 2025.1
    from homeassistant.components.zeroconf import ZeroconfServiceInfo

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
PORT_SELECTOR = vol.All(
    NumberSelector(NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)),
    vol.Coerce(int),
)


class UnsupportedDevice(MeetTwoError):
    """App too old (no device id) or API version not supported."""


def _user_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, vol.UNDEFINED)): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): PORT_SELECTOR,
            vol.Optional(CONF_PASSWORD): PASSWORD_SELECTOR,
        }
    )


class MeetTwoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MeetTwo LED."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._name: str = DEFAULT_NAME
        self._password_required = False

    async def _async_validate(self, host: str, port: int, password: str | None) -> dict[str, Any]:
        """Check that the device answers and the password works. Returns /api/help."""
        api = MeetTwoApi(async_get_clientsession(self.hass), host, port, password)
        info = await api.help()
        if not info.get("deviceId") or int(info.get("apiVersion", 0)) > SUPPORTED_API_VERSION:
            raise UnsupportedDevice
        await api.status()  # raises MeetTwoAuthError if the password is required/wrong
        return info

    async def _async_try(
        self, host: str, port: int, password: str | None, errors: dict[str, str]
    ) -> dict[str, Any] | None:
        try:
            return await self._async_validate(host, port, password)
        except MeetTwoAuthError:
            errors["base"] = "invalid_auth" if password else "password_required"
        except MeetTwoConnectionError:
            errors["base"] = "cannot_connect"
        except UnsupportedDevice:
            errors["base"] = "unsupported"
        except MeetTwoError:
            LOGGER.exception("Unexpected response from MeetTwo LED")
            errors["base"] = "unknown"
        return None

    @staticmethod
    def _entry_data(host: str, port: int, password: str | None) -> dict[str, Any]:
        data: dict[str, Any] = {CONF_HOST: host, CONF_PORT: port}
        if password:
            data[CONF_PASSWORD] = password
        return data

    # ------------------------------------------------------------------ manual setup

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            password = user_input.get(CONF_PASSWORD) or None
            info = await self._async_try(host, port, password, errors)
            if info is not None:
                await self.async_set_unique_id(info["deviceId"])
                self._abort_if_unique_id_configured(
                    updates=self._entry_data(host, port, password)
                )
                return self.async_create_entry(
                    title=info.get("deviceName") or DEFAULT_NAME,
                    data=self._entry_data(host, port, password),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input or {}),
            errors=errors,
        )

    # ------------------------------------------------------------------ zeroconf discovery

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        props = discovery_info.properties
        device_id = props.get("id")
        if not device_id:
            return self.async_abort(reason="unsupported")

        self._host = str(discovery_info.host)
        self._port = int(discovery_info.port or DEFAULT_PORT)
        self._name = props.get("name") or DEFAULT_NAME
        self._password_required = props.get("auth") == "1"

        await self.async_set_unique_id(device_id)
        # Already configured: just follow IP/port changes
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host, CONF_PORT: self._port})

        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._host is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            password = user_input.get(CONF_PASSWORD) or None
            info = await self._async_try(self._host, self._port, password, errors)
            if info is not None:
                return self.async_create_entry(
                    title=info.get("deviceName") or self._name,
                    data=self._entry_data(self._host, self._port, password),
                )
            if errors.get("base") == "password_required":
                self._password_required = True

        schema = (
            vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR})
            if self._password_required
            else vol.Schema({})
        )
        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"name": self._name, "host": f"{self._host}:{self._port}"},
        )

    # ------------------------------------------------------------------ reauth (password changed)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            password = user_input.get(CONF_PASSWORD) or None
            info = await self._async_try(
                entry.data[CONF_HOST], entry.data[CONF_PORT], password, errors
            )
            if info is not None:
                await self.async_set_unique_id(info["deviceId"])
                self._abort_if_unique_id_mismatch()
                data = self._entry_data(entry.data[CONF_HOST], entry.data[CONF_PORT], password)
                return self.async_update_reload_and_abort(entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Optional(CONF_PASSWORD): PASSWORD_SELECTOR}),
            errors=errors,
            description_placeholders={"name": entry.title},
        )

    # ------------------------------------------------------------------ reconfigure (host/port/password)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            password = user_input.get(CONF_PASSWORD) or None
            info = await self._async_try(host, port, password, errors)
            if info is not None:
                await self.async_set_unique_id(info["deviceId"])
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry, data=self._entry_data(host, port, password)
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(user_input or entry.data),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MeetTwoOptionsFlow()


class MeetTwoOptionsFlow(OptionsFlow):
    """Options: polling interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        NumberSelector(
                            NumberSelectorConfig(
                                min=MIN_SCAN_INTERVAL,
                                max=MAX_SCAN_INTERVAL,
                                step=1,
                                unit_of_measurement="s",
                                mode=NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Coerce(int),
                    )
                }
            ),
        )