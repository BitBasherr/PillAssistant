"""Test medication history editing services."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    ATTR_ACTION,
    ATTR_DOSAGE,
    ATTR_DOSAGE_UNIT,
    ATTR_END_DATE,
    ATTR_HISTORY_INDEX,
    ATTR_MEDICATION_ID,
    ATTR_START_DATE,
    ATTR_TIMESTAMP,
    DOMAIN,
    SERVICE_DELETE_MEDICATION_HISTORY,
    SERVICE_EDIT_MEDICATION_HISTORY,
    SERVICE_GET_MEDICATION_HISTORY,
    SERVICE_TAKE_MEDICATION,
    SERVICE_SKIP_MEDICATION,
    SERVICE_REFILL_MEDICATION,
)


async def test_get_medication_history(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test retrieving medication history."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Add some history entries by taking medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get history
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Verify response
    assert response is not None
    assert "history" in response
    assert "total_entries" in response
    assert response["total_entries"] > 0
    assert len(response["history"]) > 0

    # Verify each entry has required fields
    for entry in response["history"]:
        assert "medication_id" in entry
        assert "timestamp" in entry
        assert "action" in entry
        assert "history_index" in entry


async def test_get_medication_history_filtered_by_medication_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test retrieving medication history filtered by medication ID."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Add history entry
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get history filtered by medication ID
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Verify all entries match the filter
    assert response is not None
    assert "history" in response
    for entry in response["history"]:
        assert entry["medication_id"] == mock_config_entry.entry_id


async def test_get_medication_history_filtered_by_date_range(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test retrieving medication history filtered by date range."""
    from datetime import datetime, timedelta
    
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Add history entry
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get history filtered by date range
    start_date = (datetime.now() - timedelta(days=1)).isoformat()
    end_date = (datetime.now() + timedelta(days=1)).isoformat()
    
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {
            ATTR_START_DATE: start_date,
            ATTR_END_DATE: end_date,
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Verify response
    assert response is not None
    assert "history" in response
    assert response["total_entries"] > 0


async def test_edit_medication_history_timestamp(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test editing a medication history entry's timestamp."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Add history entry
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get history to find the index
    history_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert len(history_response["history"]) > 0
    first_entry = history_response["history"][0]
    history_index = first_entry["history_index"]

    # Edit the timestamp
    new_timestamp = "2024-01-15T12:00:00"
    edit_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_EDIT_MEDICATION_HISTORY,
        {
            ATTR_HISTORY_INDEX: history_index,
            ATTR_TIMESTAMP: new_timestamp,
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Verify edit was successful
    assert edit_response["success"] is True
    assert edit_response["updated_entry"]["timestamp"] == new_timestamp

    # Verify the change persisted
    verify_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Find the edited entry
    edited_entry = None
    for entry in verify_response["history"]:
        if entry["history_index"] == history_index:
            edited_entry = entry
            break

    assert edited_entry is not None
    assert edited_entry["timestamp"] == new_timestamp


async def test_edit_medication_history_action(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test editing a medication history entry's action type."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Add history entry (taken)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get history
    history_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    first_entry = history_response["history"][0]
    history_index = first_entry["history_index"]
    assert first_entry["action"] == "taken"

    # Change action to skipped
    edit_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_EDIT_MEDICATION_HISTORY,
        {
            ATTR_HISTORY_INDEX: history_index,
            ATTR_ACTION: "skipped",
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Verify edit was successful
    assert edit_response["success"] is True
    assert edit_response["updated_entry"]["action"] == "skipped"


async def test_edit_medication_history_dosage(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test editing a medication history entry's dosage."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Add history entry
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get history
    history_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    first_entry = history_response["history"][0]
    history_index = first_entry["history_index"]

    # Edit the dosage
    new_dosage = 2.5
    edit_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_EDIT_MEDICATION_HISTORY,
        {
            ATTR_HISTORY_INDEX: history_index,
            ATTR_DOSAGE: new_dosage,
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Verify edit was successful
    assert edit_response["success"] is True
    assert edit_response["updated_entry"]["dosage"] == new_dosage


async def test_edit_medication_history_invalid_index(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test editing with an invalid history index."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Try to edit with invalid index
    edit_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_EDIT_MEDICATION_HISTORY,
        {
            ATTR_HISTORY_INDEX: 99999,
            ATTR_ACTION: "skipped",
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Verify edit failed
    assert edit_response["success"] is False
    assert "error" in edit_response


async def test_delete_medication_history(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test deleting a medication history entry."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Add history entries
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SKIP_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get initial history
    history_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    initial_count = history_response["total_entries"]
    assert initial_count >= 2

    first_entry = history_response["history"][0]
    history_index = first_entry["history_index"]

    # Delete the entry
    delete_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_DELETE_MEDICATION_HISTORY,
        {ATTR_HISTORY_INDEX: history_index},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Verify deletion was successful
    assert delete_response["success"] is True
    assert "deleted_entry" in delete_response

    # Verify the entry was removed
    verify_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert verify_response["total_entries"] == initial_count - 1


async def test_delete_medication_history_invalid_index(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test deleting with an invalid history index."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Try to delete with invalid index
    delete_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_DELETE_MEDICATION_HISTORY,
        {ATTR_HISTORY_INDEX: 99999},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Verify deletion failed
    assert delete_response["success"] is False
    assert "error" in delete_response


async def test_multiple_history_edits(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test multiple edits to the same history entry."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Add history entry
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get history
    history_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    first_entry = history_response["history"][0]
    history_index = first_entry["history_index"]

    # First edit: change action
    await hass.services.async_call(
        DOMAIN,
        SERVICE_EDIT_MEDICATION_HISTORY,
        {
            ATTR_HISTORY_INDEX: history_index,
            ATTR_ACTION: "skipped",
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Second edit: change timestamp
    new_timestamp = "2024-02-01T10:00:00"
    await hass.services.async_call(
        DOMAIN,
        SERVICE_EDIT_MEDICATION_HISTORY,
        {
            ATTR_HISTORY_INDEX: history_index,
            ATTR_TIMESTAMP: new_timestamp,
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Third edit: change dosage unit
    await hass.services.async_call(
        DOMAIN,
        SERVICE_EDIT_MEDICATION_HISTORY,
        {
            ATTR_HISTORY_INDEX: history_index,
            ATTR_DOSAGE_UNIT: "mL",
        },
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Verify all changes persisted
    verify_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEDICATION_HISTORY,
        {},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    edited_entry = None
    for entry in verify_response["history"]:
        if entry["history_index"] == history_index:
            edited_entry = entry
            break

    assert edited_entry is not None
    assert edited_entry["action"] == "skipped"
    assert edited_entry["timestamp"] == new_timestamp
    assert edited_entry["dosage_unit"] == "mL"
