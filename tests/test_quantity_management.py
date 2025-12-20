"""Test quantity management features for Pill Assistant."""

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
    CONF_CURRENT_QUANTITY,
    CONF_USE_CUSTOM_QUANTITY,
)


async def test_config_flow_default_starting_quantity(hass: HomeAssistant):
    """Test that default starting quantity equals refill amount when custom quantity not checked."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
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
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    # Don't check custom quantity box
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_USE_CUSTOM_QUANTITY: False,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    # Current quantity should be set to refill amount
    assert result["data"][CONF_CURRENT_QUANTITY] == 30


async def test_config_flow_custom_starting_quantity(hass: HomeAssistant):
    """Test that custom starting quantity can be set when checkbox is checked."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "2",
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
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    # First, check the custom quantity box
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_USE_CUSTOM_QUANTITY: True,
        },
    )

    # Form should be re-shown with current quantity field
    if result["type"] == data_entry_flow.FlowResultType.FORM:
        # Now provide the custom quantity
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_REFILL_AMOUNT: 60,
                CONF_REFILL_REMINDER_DAYS: 7,
                CONF_USE_CUSTOM_QUANTITY: True,
                CONF_CURRENT_QUANTITY: 15,  # Starting with only 15 instead of 60
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CURRENT_QUANTITY] == 15
    assert result["data"][CONF_REFILL_AMOUNT] == 60


async def test_options_flow_current_quantity_editable(hass: HomeAssistant):
    """Test that current quantity can be edited in options flow."""
    # Create a medication entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Open options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    # The form should include CONF_CURRENT_QUANTITY field

    # Update the current quantity
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_CURRENT_QUANTITY: 25,  # Changed from 30 to 25
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

    # Verify the remaining amount was updated in storage
    entry_data = hass.data[DOMAIN][entry.entry_id]
    storage_data = entry_data.get("storage_data", {})
    medications = storage_data.get("medications", {})
    assert medications[entry.entry_id]["remaining_amount"] == 25


async def test_options_flow_dosage_editable(hass: HomeAssistant):
    """Test that dosage can be edited in options flow."""
    # Create a medication entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Open options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM

    # Update the dosage
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "2",  # Changed from 1 to 2
            CONF_DOSAGE_UNIT: "mg",
            CONF_CURRENT_QUANTITY: 30,
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

    # Verify the dosage was updated
    assert entry.data[CONF_DOSAGE] == "2"


async def test_remaining_amount_initialized_from_custom_quantity(hass: HomeAssistant):
    """Test that remaining_amount in storage is initialized from custom quantity."""
    # Create entry with custom quantity
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_CURRENT_QUANTITY: 20,  # Custom starting amount
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check that remaining_amount was initialized to custom quantity, not refill amount
    entry_data = hass.data[DOMAIN][entry.entry_id]
    storage_data = entry_data.get("storage_data", {})
    medications = storage_data.get("medications", {})

    assert medications[entry.entry_id]["remaining_amount"] == 20
    assert entry.data[CONF_REFILL_AMOUNT] == 60
