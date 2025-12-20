"""Test clock visualization yesterday toggle feature."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    ATTR_MEDICATION_ID,
    DOMAIN,
    SERVICE_TAKE_MEDICATION,
)


async def test_clock_yesterday_toggle_functionality(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that yesterday toggle works with clock visualization."""
    # This is a UI test that verifies the backend services support
    # the functionality needed for the yesterday toggle
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Take medication to create history
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify history was created
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    assert len(storage_data["history"]) > 0


async def test_medication_name_capitalization_in_storage(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that medication names are stored correctly for capitalization."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Take medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify medication name is stored in history
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    history_entry = storage_data["history"][0]

    assert "medication_name" in history_entry
    assert history_entry["medication_name"] == "Test Medication"


async def test_yesterday_date_filtering(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that history can be filtered by yesterday's date."""
    from datetime import datetime, timedelta

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Take medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Test filtering by yesterday's date range
    yesterday = datetime.now() - timedelta(days=1)
    start_date = yesterday.replace(hour=0, minute=0, second=0)
    end_date = yesterday.replace(hour=23, minute=59, second=59)

    # This should return empty results since we just created today's data
    response = await hass.services.async_call(
        DOMAIN,
        "get_medication_history",
        {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Should have no entries for yesterday
    assert response is not None
    assert response["total_entries"] == 0


async def test_clock_data_supports_date_selection(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that clock data can be retrieved for specific dates."""
    from datetime import datetime

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Take medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get medication history for today (which clock visualization uses)
    today = datetime.now()
    start_date = today.replace(hour=0, minute=0, second=0)
    end_date = today.replace(hour=23, minute=59, second=59)

    response = await hass.services.async_call(
        DOMAIN,
        "get_medication_history",
        {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Should have history for today
    assert response is not None
    assert response["total_entries"] > 0
    assert len(response["history"]) > 0
