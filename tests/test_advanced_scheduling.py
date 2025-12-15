"""Test advanced scheduling features for Pill Assistant."""

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
    CONF_RELATIVE_TO_MEDICATION,
    CONF_RELATIVE_TO_SENSOR,
    CONF_RELATIVE_OFFSET_HOURS,
    CONF_RELATIVE_OFFSET_MINUTES,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
)


async def test_relative_medication_schedule_config(hass: HomeAssistant):
    """Test configuring medication with relative scheduling to another medication."""
    # First, create a base medication
    base_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    
    base_result = await hass.config_entries.flow.async_configure(
        base_result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Base Medication",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
        },
    )
    
    base_result = await hass.config_entries.flow.async_configure(
        base_result["flow_id"],
        user_input={
            "schedule_type": "fixed_time",
        },
    )
    
    base_result = await hass.config_entries.flow.async_configure(
        base_result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )
    
    base_result = await hass.config_entries.flow.async_configure(
        base_result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            "create_test_button": False,
        },
    )
    
    assert base_result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    base_med_id = base_result["result"].entry_id
    
    # Now create a relative medication
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Relative Medication",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
        },
    )
    
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "schedule_type": "relative_medication",
        },
    )
    
    # Now configure relative scheduling
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_RELATIVE_TO_MEDICATION: base_med_id,
            CONF_RELATIVE_OFFSET_HOURS: 2,
            CONF_RELATIVE_OFFSET_MINUTES: 30,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )
    
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            "create_test_button": False,
        },
    )
    
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCHEDULE_TYPE] == "relative_medication"
    assert result["data"][CONF_RELATIVE_TO_MEDICATION] == base_med_id
    assert result["data"][CONF_RELATIVE_OFFSET_HOURS] == 2
    assert result["data"][CONF_RELATIVE_OFFSET_MINUTES] == 30


async def test_relative_sensor_schedule_config(hass: HomeAssistant):
    """Test configuring medication with relative scheduling to a sensor."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Sensor Based Med",
            CONF_DOSAGE: "75",
            CONF_DOSAGE_UNIT: "mg",
        },
    )
    
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "schedule_type": "relative_sensor",
        },
    )
    
    # Configure sensor-based scheduling
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_RELATIVE_TO_SENSOR: "binary_sensor.wake_up",
            CONF_RELATIVE_OFFSET_HOURS: 1,
            CONF_RELATIVE_OFFSET_MINUTES: 0,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )
    
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            "create_test_button": False,
        },
    )
    
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCHEDULE_TYPE] == "relative_sensor"
    assert result["data"][CONF_RELATIVE_TO_SENSOR] == "binary_sensor.wake_up"
    assert result["data"][CONF_RELATIVE_OFFSET_HOURS] == 1
    assert result["data"][CONF_RELATIVE_OFFSET_MINUTES] == 0


async def test_relative_medication_next_dose_calculation(hass: HomeAssistant):
    """Test next dose calculation for relative medication scheduling."""
    # Create base medication
    base_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Base Med",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    base_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_entry.entry_id)
    await hass.async_block_till_done()
    
    # Take the base medication
    await hass.services.async_call(
        DOMAIN,
        "take_medication",
        {"medication_id": base_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    
    # Create relative medication (2 hours after base)
    rel_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Relative Med",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TYPE: "relative_medication",
            CONF_RELATIVE_TO_MEDICATION: base_entry.entry_id,
            CONF_RELATIVE_OFFSET_HOURS: 2,
            CONF_RELATIVE_OFFSET_MINUTES: 0,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    rel_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(rel_entry.entry_id)
    await hass.async_block_till_done()
    
    # Get the relative medication sensor
    entity_id = "sensor.relative_med"
    state = hass.states.get(entity_id)
    
    assert state is not None
    
    # Check that next_dose_time is set (should be 2 hours after base med was taken)
    next_dose_time = state.attributes.get("next_dose_time")
    assert next_dose_time is not None, "Next dose time should be calculated based on base medication"
