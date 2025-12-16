"""Button platform for Pill Assistant."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    SERVICE_TEST_NOTIFICATION,
    ATTR_MEDICATION_ID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities for Pill Assistant."""
    # Create test notification button for this medication
    medication_name = config_entry.data.get(CONF_MEDICATION_NAME, "Unknown")

    button = PillAssistantTestButton(
        hass,
        config_entry,
        medication_name,
    )

    async_add_entities([button], True)


class PillAssistantTestButton(ButtonEntity):
    """Button entity to test medication notifications."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        medication_name: str,
    ) -> None:
        """Initialize the button."""
        self.hass = hass
        self._config_entry = config_entry
        self._medication_name = medication_name
        self._medication_id = config_entry.entry_id

        # Set unique_id and name - entity_id will be generated automatically
        self._attr_unique_id = f"{DOMAIN}_test_{config_entry.entry_id}"
        self._attr_name = f"PA_{medication_name}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._medication_id)},
            "name": f"Pill Assistant - {self._medication_name}",
            "manufacturer": "Pill Assistant",
            "model": "Medication Tracker",
        }

    @property
    def icon(self) -> str:
        """Return the icon for the button."""
        return "mdi:pill"

    async def async_press(self) -> None:
        """Handle the button press - trigger test notification."""
        _LOGGER.info(
            "Test notification button pressed for medication: %s",
            self._medication_name,
        )

        # Call the test notification service
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_TEST_NOTIFICATION,
            {ATTR_MEDICATION_ID: self._medication_id},
            blocking=True,
        )
