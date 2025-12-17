"""Test dosage adjustment services."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    SERVICE_INCREMENT_DOSAGE,
    SERVICE_DECREMENT_DOSAGE,
    ATTR_MEDICATION_ID,
    CONF_DOSAGE,
)


async def test_increment_dosage_service(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test the increment_dosage service."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial dosage
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_dosage = float(med_data.get(CONF_DOSAGE, 1))

    # Call increment_dosage service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_INCREMENT_DOSAGE,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify dosage was incremented
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_dosage = float(med_data.get(CONF_DOSAGE, 1))
    assert new_dosage == initial_dosage + 0.5


async def test_decrement_dosage_service(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test the decrement_dosage service."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial dosage
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_dosage = float(med_data.get(CONF_DOSAGE, 1))

    # Call decrement_dosage service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_DECREMENT_DOSAGE,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify dosage was decremented
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_dosage = float(med_data.get(CONF_DOSAGE, 1))
    assert new_dosage == initial_dosage - 0.5


async def test_decrement_dosage_minimum(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that dosage cannot go below 0.5."""
    # Create a new mock config entry with dosage of 0.5
    mock_config_entry = MockConfigEntry(
        domain="pill_assistant",
        data={
            "medication_name": "Test Medication",
            "dosage": "0.5",
            "dosage_unit": "mg",
            "schedule_type": "fixed_time",
            "schedule_times": ["08:00", "20:00"],
            "schedule_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "refill_amount": 30,
            "refill_reminder_days": 7,
            "notes": "Test notes",
        },
    )
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Call decrement_dosage service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_DECREMENT_DOSAGE,
        {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify dosage stayed at 0.5 (minimum)
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_dosage = float(med_data.get(CONF_DOSAGE, 1))
    assert new_dosage == 0.5


async def test_increment_dosage_multiple_times(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test incrementing dosage multiple times."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial dosage
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    initial_dosage = float(med_data.get(CONF_DOSAGE, 1))

    # Increment 3 times
    for _ in range(3):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_INCREMENT_DOSAGE,
            {ATTR_MEDICATION_ID: mock_config_entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Verify dosage was incremented 3 times
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    new_dosage = float(med_data.get(CONF_DOSAGE, 1))
    assert new_dosage == initial_dosage + 1.5


async def test_dosage_adjustment_with_invalid_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test dosage adjustment with invalid medication ID."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Try with invalid medication ID (should not crash)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_INCREMENT_DOSAGE,
        {ATTR_MEDICATION_ID: "invalid_id"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify original dosage unchanged
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    storage_data = entry_data["storage_data"]
    med_data = storage_data["medications"].get(mock_config_entry.entry_id)
    dosage = float(med_data.get(CONF_DOSAGE, 1))
    assert dosage == 100.0  # Original dosage from mock_config_entry
