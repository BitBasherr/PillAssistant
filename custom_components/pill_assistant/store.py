from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class PillAssistantStore:
    """Singleton storage manager with locking for the Pill Assistant integration.
    
    This ensures that all config entries share the same storage instance and
    prevents race conditions when multiple entries try to save at the same time.
    """

    _instance: PillAssistantStore | None = None
    _lock = asyncio.Lock()

    def __new__(cls, hass: HomeAssistant) -> PillAssistantStore:
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store (only once for the singleton)."""
        if self._initialized:
            return
        
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] | None = None
        self._initialized = True
        _LOGGER.debug("PillAssistantStore singleton initialized")

    async def async_load(self) -> dict[str, Any]:
        """Load data from storage.
        
        Returns a copy of the cached data if available, otherwise loads from disk.
        This ensures all entries work with consistent data.
        """
        async with self._lock:
            if self._data is None:
                self._data = await self._store.async_load() or {}
                self._data.setdefault("medications", {})
                self._data.setdefault("history", [])
                self._data.setdefault("last_sensor_trigger", {})
                _LOGGER.debug("Loaded storage data from disk")
            
            # Return a reference to the shared data (not a copy)
            # All entries will share the same dict instance
            return self._data

    async def async_save(self, data: dict[str, Any]) -> None:
        """Save data to storage with locking to prevent race conditions."""
        async with self._lock:
            self._data = data
            await self._store.async_save(data)
            _LOGGER.debug("Saved storage data to disk")

    async def async_update(self, update_fn: Callable[[dict[str, Any]], None]) -> None:
        """Update storage data using a callback function with proper locking.
        
        This is the coordinator-style update method that ensures atomic updates.
        The update_fn receives the current data and can modify it in place.
        
        Args:
            update_fn: A function that receives the storage data dict and modifies it.
        """
        async with self._lock:
            if self._data is None:
                self._data = await self._store.async_load() or {}
                self._data.setdefault("medications", {})
                self._data.setdefault("history", [])
                self._data.setdefault("last_sensor_trigger", {})
            
            # Call the update function to modify the data
            update_fn(self._data)
            
            # Save the updated data
            await self._store.async_save(self._data)
            _LOGGER.debug("Updated and saved storage data")

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing purposes)."""
        cls._instance = None
