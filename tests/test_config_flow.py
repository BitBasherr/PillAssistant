"""Test Pill Assistant config flow."""

import pytest
from homeassistant import config_entries, data_entry_flow
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


async def test_user_step_medication_details(hass: HomeAssistant):
    """Test the user step with medication details."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    # Test with valid input
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Aspirin",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_NOTES: "Test medication",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "schedule"


async def test_user_step_missing_medication_name(hass: HomeAssistant):
    """Test the user step with missing medication name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Test with empty medication name
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "medication_name_required"


async def test_schedule_step(hass: HomeAssistant):
    """Test the schedule configuration step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Complete user step
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Vitamin D",
            CONF_DOSAGE: "1000",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    # Test schedule step
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri"],
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "refill"


async def test_complete_flow(hass: HomeAssistant):
    """Test completing the entire config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Step 1: Medication details
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
            CONF_NOTES: "Morning medication",
        },
    )

    # Step 2: Schedule
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["09:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    # Step 3: Refill settings
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 90,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Med"
    assert result["data"][CONF_MEDICATION_NAME] == "Test Med"
    assert result["data"][CONF_DOSAGE] == "50"
    assert result["data"][CONF_REFILL_AMOUNT] == 90


async def test_duplicate_medication_rejected(hass: HomeAssistant):
    """Test that duplicate medication names are rejected."""
    # Create first entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="pill_assistant_test_med",
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["09:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)

    # Try to create duplicate
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["09:00"],
            CONF_SCHEDULE_DAYS: ["mon"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_schedule_step_with_single_time(hass: HomeAssistant):
    """Test schedule step with single time entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Morning Med",
            CONF_DOSAGE: "25",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    # Single time schedule
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["07:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri"],
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "refill"


async def test_schedule_step_with_multiple_times(hass: HomeAssistant):
    """Test schedule step with multiple time entries."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Multi-dose Med",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    # Multiple times
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00", "14:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "refill"


async def test_schedule_step_converts_string_to_list(hass: HomeAssistant):
    """Test that schedule step converts single string to list."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    # Pass string instead of list (edge case)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: "10:00",  # String instead of list
            CONF_SCHEDULE_DAYS: ["mon", "wed", "fri"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    # Verify schedule_times was converted to list
    assert isinstance(result["data"][CONF_SCHEDULE_TIMES], list)
    assert result["data"][CONF_SCHEDULE_TIMES] == ["10:00"]


async def test_schedule_step_with_empty_days_uses_default(hass: HomeAssistant):
    """Test that empty schedule days defaults to all days."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Daily Med",
            CONF_DOSAGE: "10",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    # Don't provide schedule_days
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: [],  # Empty list
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    # Should default to all days
    assert len(result["data"][CONF_SCHEDULE_DAYS]) == 7


async def test_complete_flow_with_edge_times(hass: HomeAssistant):
    """Test flow with edge case times (midnight, noon, 23:59)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Edge Time Med",
            CONF_DOSAGE: "200",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["00:00", "12:00", "23:59"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 90,
            CONF_REFILL_REMINDER_DAYS: 10,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert "00:00" in result["data"][CONF_SCHEDULE_TIMES]
    assert "23:59" in result["data"][CONF_SCHEDULE_TIMES]


async def test_complete_flow_with_weekend_only(hass: HomeAssistant):
    """Test complete flow with weekend-only schedule."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Weekend Med",
            CONF_DOSAGE: "150",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["10:00"],
            CONF_SCHEDULE_DAYS: ["sat", "sun"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 8,
            CONF_REFILL_REMINDER_DAYS: 2,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert set(result["data"][CONF_SCHEDULE_DAYS]) == {"sat", "sun"}


async def test_complete_flow_with_decimal_dosage(hass: HomeAssistant):
    """Test complete flow with decimal dosage."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Liquid Med",
            CONF_DOSAGE: "2.5",
            CONF_DOSAGE_UNIT: "mL",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DOSAGE] == "2.5"
    assert result["data"][CONF_DOSAGE_UNIT] == "mL"


async def test_complete_flow_with_various_dosage_units(hass: HomeAssistant):
    """Test complete flow with different dosage units."""
    units_to_test = ["tablet(s)", "capsule(s)", "drop(s)", "spray(s)", "puff(s)", "g"]
    
    for unit in units_to_test:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_MEDICATION_NAME: f"Test {unit} Med",
                CONF_DOSAGE: "1",
                CONF_DOSAGE_UNIT: unit,
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_SCHEDULE_TIMES: ["08:00"],
                CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_REFILL_AMOUNT: 30,
                CONF_REFILL_REMINDER_DAYS: 7,
            },
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_DOSAGE_UNIT] == unit


async def test_complete_flow_with_high_refill_settings(hass: HomeAssistant):
    """Test complete flow with high refill amount and reminder days."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Long-term Med",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 365,  # One year
            CONF_REFILL_REMINDER_DAYS: 30,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_REFILL_AMOUNT] == 365
    assert result["data"][CONF_REFILL_REMINDER_DAYS] == 30


async def test_complete_flow_with_long_medication_name(hass: HomeAssistant):
    """Test complete flow with very long medication name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    long_name = "Acetylsalicylic Acid Extended Release with Multiple Vitamins and Minerals"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: long_name,
            CONF_DOSAGE: "500",
            CONF_DOSAGE_UNIT: "mg",
            CONF_NOTES: "Take with food",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_MEDICATION_NAME] == long_name


async def test_complete_flow_with_special_characters_in_notes(hass: HomeAssistant):
    """Test complete flow with special characters in notes."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    special_notes = "Take with food! (Important) - Don't mix with alcohol. 100% effective."
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Special Notes Med",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_NOTES: special_notes,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NOTES] == special_notes


async def test_complete_flow_with_empty_notes(hass: HomeAssistant):
    """Test complete flow with empty notes field."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "No Notes Med",
            CONF_DOSAGE: "75",
            CONF_DOSAGE_UNIT: "mg",
            CONF_NOTES: "",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["12:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NOTES] == ""


async def test_complete_flow_with_alternating_days(hass: HomeAssistant):
    """Test complete flow with alternating day schedule."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Alternating Med",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "wed", "fri"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 12,
            CONF_REFILL_REMINDER_DAYS: 3,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert set(result["data"][CONF_SCHEDULE_DAYS]) == {"mon", "wed", "fri"}


async def test_complete_flow_with_minimal_refill_reminder(hass: HomeAssistant):
    """Test complete flow with minimal (1 day) refill reminder."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Daily Med",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 7,
            CONF_REFILL_REMINDER_DAYS: 1,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_REFILL_REMINDER_DAYS] == 1


async def test_config_flow_stores_all_data_correctly(hass: HomeAssistant):
    """Test that config flow stores all provided data correctly."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    test_data = {
        CONF_MEDICATION_NAME: "Complete Test Med",
        CONF_DOSAGE: "125",
        CONF_DOSAGE_UNIT: "mg",
        CONF_NOTES: "Test notes for completeness",
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=test_data
    )

    schedule_data = {
        CONF_SCHEDULE_TIMES: ["07:30", "19:30"],
        CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri"],
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=schedule_data
    )

    refill_data = {
        CONF_REFILL_AMOUNT: 60,
        CONF_REFILL_REMINDER_DAYS: 10,
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=refill_data
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    
    # Verify all data is stored
    for key, value in test_data.items():
        assert result["data"][key] == value
    for key, value in schedule_data.items():
        assert result["data"][key] == value
    for key, value in refill_data.items():
        assert result["data"][key] == value
