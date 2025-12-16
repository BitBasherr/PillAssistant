"""Test Pill Assistant options flow."""

import pytest
from homeassistant import data_entry_flow
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
    CONF_NOTES,
)
from custom_components.pill_assistant.config_flow import PillAssistantOptionsFlow


async def test_options_flow_instantiation(mock_config_entry: MockConfigEntry):
    """Test that PillAssistantOptionsFlow can be instantiated without AttributeError.

    This test specifically checks for the bug where config_entry property
    had no setter, causing AttributeError when trying to initialize the flow.
    """
    # This should not raise AttributeError
    flow = PillAssistantOptionsFlow(mock_config_entry)

    # Verify the config entry was stored correctly
    assert flow._config_entry == mock_config_entry


async def test_options_flow_init(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test the options flow initialization."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_update_dosage(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test updating medication dosage through options flow."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Update dosage
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "200",  # Changed from 100
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: "Test notes",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

    # Verify the entry was updated
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_DOSAGE] == "200"


async def test_options_flow_update_schedule(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test updating medication schedule through options flow."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Update schedule to once daily on weekdays only
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00"],  # Changed from twice daily
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri"],  # Weekdays only
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: "Test notes",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

    # Verify the entry was updated
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_SCHEDULE_TIMES] == ["08:00"]
    assert len(entry.data[CONF_SCHEDULE_DAYS]) == 5


async def test_options_flow_update_refill_settings(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test updating refill settings through options flow."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Update refill settings
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 90,  # Changed from 30
            CONF_REFILL_REMINDER_DAYS: 14,  # Changed from 7
            CONF_NOTES: "Updated notes",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

    # Verify the entry was updated
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_REFILL_AMOUNT] == 90
    assert entry.data[CONF_REFILL_REMINDER_DAYS] == 14
    assert entry.data[CONF_NOTES] == "Updated notes"


async def test_options_flow_with_single_schedule_time(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow with a single schedule time."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Update with single schedule time
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["12:00"],
            CONF_SCHEDULE_DAYS: ["mon", "wed", "fri"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: "Single dose daily",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_SCHEDULE_TIMES] == ["12:00"]
    assert len(entry.data[CONF_SCHEDULE_DAYS]) == 3


async def test_options_flow_with_multiple_schedule_times(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow with multiple schedule times."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Update with multiple schedule times (4 times a day)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["06:00", "12:00", "18:00", "22:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 120,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: "Four times daily",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert len(entry.data[CONF_SCHEDULE_TIMES]) == 4
    assert entry.data[CONF_SCHEDULE_TIMES] == ["06:00", "12:00", "18:00", "22:00"]


async def test_options_flow_with_empty_notes(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow can handle empty notes field."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Update with empty notes
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: "",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_NOTES] == ""


async def test_options_flow_with_different_dosage_units(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow with different dosage units."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Test with mL
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Liquid Medicine",
            CONF_DOSAGE: "5",
            CONF_DOSAGE_UNIT: "mL",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 100,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: "Liquid form",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_DOSAGE_UNIT] == "mL"
    assert entry.data[CONF_MEDICATION_NAME] == "Liquid Medicine"


async def test_options_flow_with_high_refill_amount(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow with high refill amounts."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Test with large refill amount
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 365,  # One year supply
            CONF_REFILL_REMINDER_DAYS: 30,
            CONF_NOTES: "Annual prescription",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_REFILL_AMOUNT] == 365
    assert entry.data[CONF_REFILL_REMINDER_DAYS] == 30


async def test_options_flow_with_weekend_only_schedule(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow with weekend-only medication schedule."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Update to weekend only
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Weekend Medication",
            CONF_DOSAGE: "200",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["10:00"],
            CONF_SCHEDULE_DAYS: ["sat", "sun"],
            CONF_REFILL_AMOUNT: 8,
            CONF_REFILL_REMINDER_DAYS: 2,
            CONF_NOTES: "Weekend only",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert len(entry.data[CONF_SCHEDULE_DAYS]) == 2
    assert set(entry.data[CONF_SCHEDULE_DAYS]) == {"sat", "sun"}


async def test_options_flow_preserves_existing_data_on_display(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that options flow displays current values correctly."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Verify the form shows current data as defaults
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"
    
    # The schema should have defaults matching current config
    schema = result["data_schema"].schema
    for key, value in schema.items():
        if key == CONF_MEDICATION_NAME:
            assert value.default == "Test Medication"
        elif key == CONF_DOSAGE:
            assert value.default == "100"
        elif key == CONF_DOSAGE_UNIT:
            assert value.default == "mg"
        elif key == CONF_SCHEDULE_TIMES:
            assert value.default == ["08:00", "20:00"]
        elif key == CONF_REFILL_AMOUNT:
            assert value.default == 30


async def test_options_flow_with_minimal_refill_reminder(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow with minimal refill reminder days."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Set refill reminder to 1 day
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 7,
            CONF_REFILL_REMINDER_DAYS: 1,
            CONF_NOTES: "Daily medication",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_REFILL_REMINDER_DAYS] == 1


async def test_options_flow_with_various_time_formats(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow handles various time formats in schedule."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Test with midnight and noon times
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["00:00", "12:00", "23:59"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 90,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: "Edge time tests",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert "00:00" in entry.data[CONF_SCHEDULE_TIMES]
    assert "23:59" in entry.data[CONF_SCHEDULE_TIMES]


async def test_options_flow_updates_entry_data_not_options(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that options flow updates entry.data, not entry.options."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Updated Name",
            CONF_DOSAGE: "150",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["09:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri"],
            CONF_REFILL_AMOUNT: 50,
            CONF_REFILL_REMINDER_DAYS: 10,
            CONF_NOTES: "Updated notes",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    
    # Verify data is in entry.data, not entry.options
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_MEDICATION_NAME] == "Updated Name"
    assert entry.data[CONF_DOSAGE] == "150"
    # Options should be empty
    assert len(entry.options) == 0


async def test_options_flow_with_alternating_days(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow with alternating day schedule."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Set to alternating days (Mon, Wed, Fri)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Alternating Medication",
            CONF_DOSAGE: "75",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "wed", "fri"],
            CONF_REFILL_AMOUNT: 24,
            CONF_REFILL_REMINDER_DAYS: 5,
            CONF_NOTES: "Every other day schedule",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert len(entry.data[CONF_SCHEDULE_DAYS]) == 3
    assert set(entry.data[CONF_SCHEDULE_DAYS]) == {"mon", "wed", "fri"}


async def test_options_flow_config_entry_attribute_access(
    mock_config_entry: MockConfigEntry,
):
    """Test that _config_entry attribute is properly accessible."""
    flow = PillAssistantOptionsFlow(mock_config_entry)
    
    # Verify internal attribute is set
    assert hasattr(flow, "_config_entry")
    assert flow._config_entry == mock_config_entry
    assert flow._config_entry.data[CONF_MEDICATION_NAME] == "Test Medication"


async def test_options_flow_with_decimal_dosage(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow with decimal dosage values."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Test with decimal dosage
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "2.5",
            CONF_DOSAGE_UNIT: "mL",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: "Decimal dosage",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_DOSAGE] == "2.5"


async def test_options_flow_long_medication_name(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow with very long medication name."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    long_name = "Acetylsalicylic Acid Extended Release with Vitamin C and Magnesium"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: long_name,
            CONF_DOSAGE: "500",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: "Long name test",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_MEDICATION_NAME] == long_name


async def test_options_flow_special_characters_in_notes(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow handles special characters in notes field."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    special_notes = "Take with food! (Important) - Don't take with milk. 100% effective."
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: special_notes,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.data[CONF_NOTES] == special_notes
