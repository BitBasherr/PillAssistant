"""Test edit medication navigation functionality."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    CONF_SCHEDULE_TYPE,
)


async def test_edit_medication_entry_id_availability(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that medication config entry ID is accessible for edit navigation."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify the entry exists and has a valid entry_id
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    assert entry.entry_id == mock_config_entry.entry_id
    assert entry.entry_id  # Should not be empty


async def test_medication_sensor_exposes_entry_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that medication sensor exposes entry_id in attributes."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get the sensor state
    entity_id = f"sensor.pa_{mock_config_entry.data[CONF_MEDICATION_NAME].lower().replace(' ', '_')}"
    state = hass.states.get(entity_id)

    assert state is not None
    # The sensor should expose the medication ID (which is the entry_id)
    assert "Medication ID" in state.attributes
    assert state.attributes["Medication ID"] == mock_config_entry.entry_id


async def test_options_flow_accessible_with_entry_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that options flow can be accessed using entry_id."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Attempt to initialize options flow using entry_id
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Should successfully show the options form
    assert result["type"] == "form"
    assert result["step_id"] == "init"


async def test_multiple_medications_have_unique_entry_ids(hass: HomeAssistant):
    """Test that multiple medications have unique entry IDs for proper navigation."""
    # Create first medication
    entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Medication One",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
        unique_id="pill_assistant_medication_one",
    )
    entry1.add_to_hass(hass)
    await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    # Create second medication
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Medication Two",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
        unique_id="pill_assistant_medication_two",
    )
    entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    # Verify they have different entry IDs
    assert entry1.entry_id != entry2.entry_id

    # Verify both can be retrieved
    retrieved_entry1 = hass.config_entries.async_get_entry(entry1.entry_id)
    retrieved_entry2 = hass.config_entries.async_get_entry(entry2.entry_id)

    assert retrieved_entry1 is not None
    assert retrieved_entry2 is not None
    assert retrieved_entry1.data[CONF_MEDICATION_NAME] == "Medication One"
    assert retrieved_entry2.data[CONF_MEDICATION_NAME] == "Medication Two"


async def test_edit_medication_preserves_existing_data(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that editing a medication via options flow preserves existing data."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get original data
    original_name = mock_config_entry.data[CONF_MEDICATION_NAME]

    # Initialize options flow
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Configure with updated dosage only
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: original_name,
            CONF_DOSAGE: "150",  # Changed
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    # Verify update was successful
    assert result["type"] == "create_entry"

    # Verify entry was updated with new dosage
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_DOSAGE] == "150"
    # Verify name was preserved
    assert entry.data[CONF_MEDICATION_NAME] == original_name
