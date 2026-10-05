"""Async client for the MeetTwo LED HTTP API."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

REQUEST_TIMEOUT = 10


class MeetTwoError(Exception):
    """Generic API error."""


class MeetTwoConnectionError(MeetTwoError):
    """Device not reachable."""


class MeetTwoAuthError(MeetTwoError):
    """Password missing or wrong."""


class MeetTwoApi:
    """Minimal client for the MeetTwo LED API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        password: str | None = None,
    ) -> None:
        self._session = session
        self.host = host
        self.port = port
        self._password = password or None

    @property
    def base_url(self) -> str:
        """Base URL of the device."""
        host = f"[{self.host}]" if ":" in self.host else self.host  # IPv6
        return f"http://{host}:{self.port}"

    async def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        headers = {"X-API-Key": self._password} if self._password else {}
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.request(
                    method, f"{self.base_url}{path}", json=payload, headers=headers
                ) as resp:
                    if resp.status == 401:
                        raise MeetTwoAuthError("Invalid or missing password")
                    try:
                        data = await resp.json(content_type=None)
                    except (aiohttp.ContentTypeError, ValueError) as err:
                        raise MeetTwoError(
                            f"Unexpected response (HTTP {resp.status})"
                        ) from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MeetTwoConnectionError(
                f"Cannot connect to {self.base_url}: {err}"
            ) from err

        if not isinstance(data, dict):
            raise MeetTwoError("Unexpected response format")
        if data.get("ok") is False:
            raise MeetTwoError(data.get("error") or "Unknown error")
        return data

    async def help(self) -> dict[str, Any]:
        """Device info (deviceId, deviceName, apiVersion, passwordRequired). No auth needed."""
        return await self._request("GET", "/api/help")

    async def status(self) -> dict[str, Any]:
        """Current LED state."""
        return (await self._request("GET", "/api/status"))["state"]

    async def effects(self) -> dict[str, str]:
        """Available effects (id -> description)."""
        return (await self._request("GET", "/api/effects"))["effects"]

    async def set(self, **params: Any) -> dict[str, Any]:
        """Change the state (see /api/set) and return the new state."""
        return (await self._request("POST", "/api/set", params))["state"]