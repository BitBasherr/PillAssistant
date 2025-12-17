"""Test notification action handlers."""

import pytest
from homeassistant.core import HomeAssistant, Event
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    SERVICE_TAKE_MEDICATION,
    SERVICE_SKIP_MEDICATION,
    SERVICE_SNOOZE_MEDICATION,
    ATTR_MEDICATION_ID,
)


async def test_notification_action_take_medication(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test notification action for taking medication."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial state
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_remaining = med_data.get("remaining_amount")

    # Simulate mobile_app notification action event
    event_data = {
        "action": f"take_medication_{mock_config_entry.entry_id}",
    }
    hass.bus.async_fire("mobile_app_notification_action", event_data)
    await hass.async_block_till_done()

    # Verify medication was taken (remaining amount decreased)
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_remaining = med_data.get("remaining_amount")
    assert new_remaining == initial_remaining - 1
    assert med_data.get("last_taken") is not None


async def test_notification_action_skip_medication(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test notification action for skipping medication."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial state
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_remaining = med_data.get("remaining_amount")
    initial_history_count = len(storage_data.get("history", []))

    # Simulate mobile_app notification action event
    event_data = {
        "action": f"skip_medication_{mock_config_entry.entry_id}",
    }
    hass.bus.async_fire("mobile_app_notification_action", event_data)
    await hass.async_block_till_done()

    # Verify medication was skipped (remaining amount unchanged, history added)
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_remaining = med_data.get("remaining_amount")
    assert new_remaining == initial_remaining
    new_history_count = len(storage_data.get("history", []))
    assert new_history_count == initial_history_count + 1


async def test_notification_action_snooze_medication(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test notification action for snoozing medication."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial state
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_snooze = med_data.get("snooze_until")

    # Simulate mobile_app notification action event
    event_data = {
        "action": f"snooze_medication_{mock_config_entry.entry_id}",
    }
    hass.bus.async_fire("mobile_app_notification_action", event_data)
    await hass.async_block_till_done()

    # Verify medication was snoozed
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_snooze = med_data.get("snooze_until")
    assert new_snooze is not None
    assert new_snooze != initial_snooze


async def test_notification_action_ios_fired(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test notification action from iOS device."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial state
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_remaining = med_data.get("remaining_amount")

    # Simulate iOS notification action event
    event_data = {
        "action": f"take_medication_{mock_config_entry.entry_id}",
    }
    hass.bus.async_fire("ios.notification_action_fired", event_data)
    await hass.async_block_till_done()

    # Verify medication was taken
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_remaining = med_data.get("remaining_amount")
    assert new_remaining == initial_remaining - 1


async def test_notification_action_invalid_medication(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test notification action with invalid medication ID."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial state
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_remaining = med_data.get("remaining_amount")

    # Simulate notification action event with invalid ID
    event_data = {
        "action": "take_medication_invalid_id_12345",
    }
    hass.bus.async_fire("mobile_app_notification_action", event_data)
    await hass.async_block_till_done()

    # Verify state unchanged (no error raised)
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_remaining = med_data.get("remaining_amount")
    assert new_remaining == initial_remaining


async def test_notification_action_no_action_field(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test notification action event without action field."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial state
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_remaining = med_data.get("remaining_amount")

    # Simulate notification action event without action field
    event_data = {}
    hass.bus.async_fire("mobile_app_notification_action", event_data)
    await hass.async_block_till_done()

    # Verify state unchanged
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_remaining = med_data.get("remaining_amount")
    assert new_remaining == initial_remaining


async def test_notification_action_unknown_action_type(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test notification action with unknown action type."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial state
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_remaining = med_data.get("remaining_amount")

    # Simulate notification action event with unknown action type
    event_data = {
        "action": f"unknown_action_{mock_config_entry.entry_id}",
    }
    hass.bus.async_fire("mobile_app_notification_action", event_data)
    await hass.async_block_till_done()

    # Verify state unchanged
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_remaining = med_data.get("remaining_amount")
    assert new_remaining == initial_remaining
