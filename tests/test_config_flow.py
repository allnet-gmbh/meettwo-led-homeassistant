"""Config flow tests."""

from __future__ import annotations

from ipaddress import ip_address
from unittest.mock import AsyncMock

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meettwo_led.api import MeetTwoAuthError, MeetTwoConnectionError
from custom_components.meettwo_led.const import DOMAIN

from .conftest import DEVICE_ID, HELP


def _zeroconf(auth: str = "0", host: str = "10.0.0.5") -> ZeroconfServiceInfo:
    return ZeroconfServiceInfo(
        ip_address=ip_address(host),
        ip_addresses=[ip_address(host)],
        hostname="Android_X.local.",
        name="Meeting Room._meettwo-led._tcp.local.",
        port=8080,
        type="_meettwo-led._tcp.local.",
        properties={"id": DEVICE_ID, "name": "Meeting Room", "api": "1", "auth": auth},
    )


async def test_user_flow(hass: HomeAssistant, mock_api: dict[str, AsyncMock]) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.5", CONF_PORT: 8080}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Meeting Room"
    assert result["data"] == {CONF_HOST: "10.0.0.5", CONF_PORT: 8080}
    assert result["result"].unique_id == DEVICE_ID


async def test_user_flow_with_password(hass: HomeAssistant, mock_api: dict[str, AsyncMock]) -> None:
    mock_api["status"].side_effect = MeetTwoAuthError
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.5", CONF_PORT: 8080}
    )
    assert result["errors"] == {"base": "password_required"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.5", CONF_PORT: 8080, CONF_PASSWORD: "wrong"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    mock_api["status"].side_effect = None
    mock_api["status"].return_value = {}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.5", CONF_PORT: 8080, CONF_PASSWORD: "secret"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PASSWORD] == "secret"


async def test_user_flow_cannot_connect(hass: HomeAssistant, mock_api: dict[str, AsyncMock]) -> None:
    mock_api["help"].side_effect = MeetTwoConnectionError
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.99", CONF_PORT: 8080}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_unsupported_app(hass: HomeAssistant, mock_api: dict[str, AsyncMock]) -> None:
    mock_api["help"].return_value = {k: v for k, v in HELP.items() if k != "deviceId"}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.5", CONF_PORT: 8080}
    )
    assert result["errors"] == {"base": "unsupported"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_api: dict[str, AsyncMock], config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.6", CONF_PORT: 8080}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_HOST] == "10.0.0.6"


async def test_zeroconf_flow(hass: HomeAssistant, mock_api: dict[str, AsyncMock]) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=_zeroconf()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: "10.0.0.5", CONF_PORT: 8080}


async def test_zeroconf_flow_with_password(hass: HomeAssistant, mock_api: dict[str, AsyncMock]) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=_zeroconf(auth="1")
    )
    assert CONF_PASSWORD in result["data_schema"].schema
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PASSWORD: "secret"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PASSWORD] == "secret"


async def test_zeroconf_updates_host(
    hass: HomeAssistant, mock_api: dict[str, AsyncMock], config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=_zeroconf(host="10.0.0.42")
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_HOST] == "10.0.0.42"


async def test_reauth(hass: HomeAssistant, mock_api: dict[str, AsyncMock], config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PASSWORD: "new"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "new"


async def test_options(hass: HomeAssistant, mock_api: dict[str, AsyncMock], config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 30})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {"scan_interval": 30}