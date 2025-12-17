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
    CONF_SCHEDULE_TYPE,
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

    # Select schedule type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "schedule_type": "fixed_time",
        },
    )

    # Test schedule_fixed step
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

    # Step 2: Schedule type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "schedule_type": "fixed_time",
        },
    )

    # Step 3: Fixed time schedule
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["09:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    # Step 4: Refill settings
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
            CONF_SCHEDULE_TYPE: "fixed_time",
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
            "schedule_type": "fixed_time",
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


async def test_config_flow_with_test_button(hass: HomeAssistant):
    """Test config flow creates button entity automatically."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Step 1: Medication details
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Button Test Med",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    # Step 2: Schedule type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "schedule_type": "fixed_time",
        },
    )

    # Step 3: Fixed time schedule
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    # Step 4: Refill settings
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    # Entry should be created successfully
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Button Test Med"

    # Set up the entry to create the button entity
    entry_id = result["result"].entry_id
    await hass.async_block_till_done()

    # Verify button entity is created with PA_ prefix
    button_entity_id = "button.pa_button_test_med"
    button_state = hass.states.get(button_entity_id)
    assert button_state is not None
    assert button_state.name == "PA_Button Test Med"
