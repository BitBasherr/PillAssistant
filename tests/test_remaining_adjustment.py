"""Test remaining amount adjustment services."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    SERVICE_INCREMENT_REMAINING,
    SERVICE_DECREMENT_REMAINING,
    ATTR_MEDICATION_ID,
    CONF_DOSAGE,
)


async def test_increment_remaining_service(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test the increment_remaining service."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial remaining amount
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_remaining = float(med_data.get("remaining_amount", 0))
    dosage = float(med_data.get(CONF_DOSAGE, 1))

    # Call increment_remaining service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_INCREMENT_REMAINING,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify remaining was incremented by dosage amount
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_remaining = float(med_data.get("remaining_amount", 0))
    assert new_remaining == initial_remaining + dosage


async def test_decrement_remaining_service(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test the decrement_remaining service."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Set initial remaining amount to be higher than dosage
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    dosage = float(med_data.get(CONF_DOSAGE, 1))
    med_data["remaining_amount"] = dosage * 3  # Set to 3x dosage
    initial_remaining = float(med_data.get("remaining_amount", 0))

    # Call decrement_remaining service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_DECREMENT_REMAINING,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify remaining was decremented by dosage amount
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_remaining = float(med_data.get("remaining_amount", 0))
    assert new_remaining == initial_remaining - dosage


async def test_decrement_remaining_minimum(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that remaining amount cannot go below 0."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Set remaining amount to 0.5
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    med_data["remaining_amount"] = 0.5

    # Call decrement_remaining service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_DECREMENT_REMAINING,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify remaining stayed at 0 (minimum)
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_remaining = float(med_data.get("remaining_amount", 0))
    assert new_remaining == 0


async def test_increment_remaining_multiple_times(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test incrementing remaining amount multiple times."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial remaining amount
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_remaining = float(med_data.get("remaining_amount", 0))
    dosage = float(med_data.get(CONF_DOSAGE, 1))

    # Increment 3 times
    for _ in range(3):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_INCREMENT_REMAINING,
            {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Verify remaining was incremented 3 times
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_remaining = float(med_data.get("remaining_amount", 0))
    assert new_remaining == initial_remaining + (dosage * 3)


async def test_remaining_adjustment_with_invalid_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test remaining adjustment with invalid medication ID."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get original remaining amount
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    original_remaining = float(med_data.get("remaining_amount", 0))

    # Try with invalid medication ID (should not crash)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_INCREMENT_REMAINING,
        {ATTR_MEDICATION_ID: "invalid_id"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify original remaining unchanged
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    remaining = float(med_data.get("remaining_amount", 0))
    assert remaining == original_remaining
