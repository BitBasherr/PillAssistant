from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION


class PillAssistantStore:
    """Small wrapper around Home Assistant's storage helper."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load(self) -> dict[str, Any]:
        data = await self._store.async_load() or {}
        data.setdefault("medications", {})
        data.setdefault("history", [])
        return data

    async def async_save(self, data: dict[str, Any]) -> None:
        await self._store.async_save(data)
