"""Test Pill Assistant initialization."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    ATTR_MEDICATION_ID,
    DOMAIN,
    LOG_FILE_NAME,
    SERVICE_TAKE_MEDICATION,
)


async def test_setup_entry(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test setting up a config entry."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state.name == "LOADED"


async def test_unload_entry(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test unloading a config entry."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state.name == "NOT_LOADED"


async def test_panel_registered_admin_only(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Ensure the admin sidebar panel is registered once."""

    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.pill_assistant.__init__.async_register_panel",
        AsyncMock(),
    ) as register:
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert register.await_count == 1
    args, kwargs = register.await_args
    assert kwargs["require_admin"] is True
    assert kwargs["frontend_url_path"] == "pill-assistant"


async def test_csv_log_written(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Ensure medication actions append to a CSV log file."""

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    log_path = Path(hass.config.path(LOG_FILE_NAME))
    assert log_path.exists()
    log_lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert log_lines[0].startswith("timestamp,event,medication_name,dosage,dosage_unit")
    assert any("TAKEN" in line for line in log_lines[1:])
