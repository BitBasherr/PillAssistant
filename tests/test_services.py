"""Test Pill Assistant services."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    SERVICE_TAKE_MEDICATION,
    SERVICE_SKIP_MEDICATION,
    SERVICE_REFILL_MEDICATION,
    ATTR_MEDICATION_ID,
    CONF_REFILL_AMOUNT,
)


async def test_take_medication_service(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test the take_medication service."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial state
    entity_id = "sensor.pa_test_medication"
    state = hass.states.get(entity_id)
    initial_remaining = state.attributes.get("remaining_amount")

    # Call take_medication service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Trigger sensor update by calling the internal update
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]

    # Verify storage was updated
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    assert med_data["remaining_amount"] == initial_remaining - 1
    assert med_data["last_taken"] is not None


async def test_take_medication_multiple_times(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test taking medication multiple times."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.pa_test_medication"
    state = hass.states.get(entity_id)
    initial_remaining = state.attributes.get("remaining_amount")

    # Take medication 3 times
    for _ in range(3):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TAKE_MEDICATION,
            {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Verify storage updated
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    assert med_data["remaining_amount"] == initial_remaining - 3


async def test_take_medication_cant_go_negative(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that remaining amount cannot go negative."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.pa_test_medication"

    # Take medication more times than available
    for _ in range(35):  # More than the 30 in refill_amount
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TAKE_MEDICATION,
            {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
            blocking=True,
        )
    await hass.async_block_till_done()

    # Verify storage has remaining amount at 0, not negative
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    assert med_data["remaining_amount"] == 0


async def test_skip_medication_service(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test the skip_medication service."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.pa_test_medication"
    state = hass.states.get(entity_id)
    initial_remaining = state.attributes.get("remaining_amount")

    # Call skip_medication service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SKIP_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )

    # Verify remaining amount did not change
    state = hass.states.get(entity_id)
    new_remaining = state.attributes.get("remaining_amount")
    assert new_remaining == initial_remaining


async def test_refill_medication_service(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test the refill_medication service."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.pa_test_medication"

    # Take some medication first
    for _ in range(10):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TAKE_MEDICATION,
            {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
            blocking=True,
        )
    await hass.async_block_till_done()

    # Verify storage shows remaining is less than refill amount
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    assert med_data["remaining_amount"] == 20

    # Call refill_medication service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFILL_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify storage shows remaining amount reset to refill amount
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    refill_amount = mock_config_entry.data[CONF_REFILL_AMOUNT]
    assert med_data["remaining_amount"] == refill_amount


async def test_service_with_invalid_medication_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test services with invalid medication ID."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Try with invalid medication ID (should not crash)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: "invalid_id"},
        blocking=True,
    )

    # Service should handle gracefully - verify original state unchanged
    entity_id = "sensor.pa_test_medication"
    state = hass.states.get(entity_id)
    assert state.attributes.get("remaining_amount") == 30


async def test_medication_history_tracking(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that medication events are tracked in history."""
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

    # Skip medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SKIP_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )

    # Refill medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFILL_MEDICATION,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )

    # Verify history was updated
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    history = storage_data.get("history", [])

    # Should have 3 history entries
    assert len(history) >= 3

    # Verify action types
    actions = [h["action"] for h in history[-3:]]
    assert "taken" in actions
    assert "skipped" in actions
    assert "refilled" in actions
