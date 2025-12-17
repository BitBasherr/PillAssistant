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


async def test_options_flow_with_test_button(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test options flow - button entity should already exist."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Update medication settings
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTES: "Test notes",
        },
    )

    # Options flow should complete successfully
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

    # Verify button entity still exists after reconfiguration
    button_entity_id = "button.pa_test_medication"
    button_state = hass.states.get(button_entity_id)
    assert button_state is not None
