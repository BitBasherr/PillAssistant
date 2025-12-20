"""Test sensor event enhancements for Pill Assistant."""

import pytest
from datetime import datetime, timedelta
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_SCHEDULE_TYPE,
    CONF_SCHEDULE_DAYS,
    CONF_RELATIVE_TO_SENSOR,
    CONF_RELATIVE_OFFSET_HOURS,
    CONF_RELATIVE_OFFSET_MINUTES,
    CONF_SENSOR_TRIGGER_VALUE,
    CONF_SENSOR_TRIGGER_ATTRIBUTE,
    CONF_AVOID_DUPLICATE_TRIGGERS,
    CONF_IGNORE_UNAVAILABLE,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
)


async def test_sensor_event_with_trigger_value(hass: HomeAssistant):
    """Test sensor event scheduling with specific trigger value."""
    # Create a mock binary sensor
    hass.states.async_set("binary_sensor.test_wake", "on")
    
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Wake-up Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "schedule_type": "relative_sensor",
        },
    )

    # Configure sensor-based scheduling with trigger value
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_RELATIVE_TO_SENSOR: "binary_sensor.test_wake",
            CONF_SENSOR_TRIGGER_VALUE: "on",
            CONF_RELATIVE_OFFSET_HOURS: 0,
            CONF_RELATIVE_OFFSET_MINUTES: 30,
            CONF_AVOID_DUPLICATE_TRIGGERS: True,
            CONF_IGNORE_UNAVAILABLE: True,
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
    assert result["data"][CONF_SCHEDULE_TYPE] == "relative_sensor"
    assert result["data"][CONF_RELATIVE_TO_SENSOR] == "binary_sensor.test_wake"
    assert result["data"][CONF_SENSOR_TRIGGER_VALUE] == "on"
    assert result["data"][CONF_AVOID_DUPLICATE_TRIGGERS] is True
    assert result["data"][CONF_IGNORE_UNAVAILABLE] is True


async def test_sensor_event_with_attribute(hass: HomeAssistant):
    """Test sensor event scheduling monitoring an attribute."""
    # Create a mock sensor with attributes
    hass.states.async_set(
        "sensor.test_sensor",
        "active",
        attributes={"battery": 90, "signal_strength": "high"}
    )
    
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Attribute Med",
            CONF_DOSAGE: "2",
            CONF_DOSAGE_UNIT: "mg",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "schedule_type": "relative_sensor",
        },
    )

    # Configure sensor-based scheduling with attribute monitoring
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_RELATIVE_TO_SENSOR: "sensor.test_sensor",
            CONF_SENSOR_TRIGGER_ATTRIBUTE: "signal_strength",
            CONF_SENSOR_TRIGGER_VALUE: "high",
            CONF_RELATIVE_OFFSET_HOURS: 1,
            CONF_RELATIVE_OFFSET_MINUTES: 0,
            CONF_AVOID_DUPLICATE_TRIGGERS: False,
            CONF_IGNORE_UNAVAILABLE: True,
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
    assert result["data"][CONF_SENSOR_TRIGGER_ATTRIBUTE] == "signal_strength"
    assert result["data"][CONF_SENSOR_TRIGGER_VALUE] == "high"


async def test_ignore_unavailable_states(hass: HomeAssistant):
    """Test that unavailable states are ignored when configured."""
    # Create a medication with sensor schedule
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TYPE: "relative_sensor",
            CONF_RELATIVE_TO_SENSOR: "sensor.test_unavailable",
            CONF_RELATIVE_OFFSET_HOURS: 0,
            CONF_RELATIVE_OFFSET_MINUTES: 30,
            CONF_IGNORE_UNAVAILABLE: True,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    
    # Set sensor to unavailable
    hass.states.async_set("sensor.test_unavailable", "unavailable")
    
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Get the medication sensor
    entity_id = "sensor.pa_test_med"
    state = hass.states.get(entity_id)

    assert state is not None
    # Next dose should be None since sensor is unavailable and we're ignoring it
    next_dose_time = state.attributes.get("Next dose time")
    assert next_dose_time is None or next_dose_time == "Not scheduled"


async def test_all_entity_types_supported(hass: HomeAssistant):
    """Test that all entity types can be used for sensor schedules."""
    # Test with various entity types
    entity_types = [
        "sensor.test",
        "binary_sensor.test",
        "input_boolean.test",
        "switch.test",
        "light.test",
    ]
    
    for entity_id in entity_types:
        hass.states.async_set(entity_id, "on")
        
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_MEDICATION_NAME: f"Med for {entity_id}",
                CONF_DOSAGE: "1",
                CONF_DOSAGE_UNIT: "each",
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "schedule_type": "relative_sensor",
            },
        )

        # Should accept any entity type
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_RELATIVE_TO_SENSOR: entity_id,
                CONF_RELATIVE_OFFSET_HOURS: 0,
                CONF_RELATIVE_OFFSET_MINUTES: 30,
                CONF_AVOID_DUPLICATE_TRIGGERS: True,
                CONF_IGNORE_UNAVAILABLE: True,
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
        assert result["data"][CONF_RELATIVE_TO_SENSOR] == entity_id
