"""Test entity name formatting functionality."""

import pytest
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TYPE,
    CONF_RELATIVE_TO_SENSOR,
    CONF_RELATIVE_OFFSET_HOURS,
    CONF_RELATIVE_OFFSET_MINUTES,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
)


async def test_entity_name_with_friendly_name(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that entity friendly name is used when available."""
    # Create a binary sensor with a friendly name
    hass.states.async_set(
        "binary_sensor.bedroom_motion",
        "on",
        {"friendly_name": "Bedroom Motion Sensor"}
    )
    
    # Create medication config entry with relative_sensor schedule
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill",
            CONF_SCHEDULE_TYPE: "relative_sensor",
            CONF_RELATIVE_TO_SENSOR: "binary_sensor.bedroom_motion",
            CONF_RELATIVE_OFFSET_HOURS: 1,
            CONF_RELATIVE_OFFSET_MINUTES: 0,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
        unique_id="pill_assistant_test_med_friendly",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    # Get the sensor state and check the Schedule attribute
    entity_id = f"sensor.pa_{entry.data[CONF_MEDICATION_NAME].lower().replace(' ', '_')}"
    state = hass.states.get(entity_id)
    
    assert state is not None
    schedule = state.attributes.get("Schedule")
    assert schedule is not None
    # Should use friendly name instead of entity ID
    assert "Bedroom Motion Sensor" in schedule
    assert "binary_sensor.bedroom_motion" not in schedule


async def test_entity_name_without_friendly_name_formats_entity_id(
    hass: HomeAssistant
):
    """Test that entity ID is formatted nicely when no friendly name exists."""
    # Create a binary sensor WITHOUT a friendly name
    hass.states.async_set(
        "binary_sensor.bedroom_motion_detector",
        "on",
        {}  # No friendly_name attribute
    )
    
    # Create medication config entry with relative_sensor schedule
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill",
            CONF_SCHEDULE_TYPE: "relative_sensor",
            CONF_RELATIVE_TO_SENSOR: "binary_sensor.bedroom_motion_detector",
            CONF_RELATIVE_OFFSET_HOURS: 2,
            CONF_RELATIVE_OFFSET_MINUTES: 30,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
        unique_id="pill_assistant_test_med_formatted",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    # Get the sensor state and check the Schedule attribute
    entity_id = f"sensor.pa_{entry.data[CONF_MEDICATION_NAME].lower().replace(' ', '_')}"
    state = hass.states.get(entity_id)
    
    assert state is not None
    schedule = state.attributes.get("Schedule")
    assert schedule is not None
    # Should format entity ID nicely: "Bedroom Motion Detector"
    assert "Bedroom Motion Detector" in schedule
    # Should NOT contain the raw entity ID
    assert "binary_sensor.bedroom_motion_detector" not in schedule


async def test_entity_name_with_underscores_in_name(hass: HomeAssistant):
    """Test entity name formatting with multiple underscores."""
    # Create entity without friendly name
    hass.states.async_set(
        "sensor.living_room_temperature_sensor",
        "72",
        {}
    )
    
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Temperature Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill",
            CONF_SCHEDULE_TYPE: "relative_sensor",
            CONF_RELATIVE_TO_SENSOR: "sensor.living_room_temperature_sensor",
            CONF_RELATIVE_OFFSET_HOURS: 0,
            CONF_RELATIVE_OFFSET_MINUTES: 15,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
        unique_id="pill_assistant_temperature_med",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    entity_id = f"sensor.pa_{entry.data[CONF_MEDICATION_NAME].lower().replace(' ', '_')}"
    state = hass.states.get(entity_id)
    
    assert state is not None
    schedule = state.attributes.get("Schedule")
    assert schedule is not None
    # Should format as "Living Room Temperature Sensor"
    assert "Living Room Temperature Sensor" in schedule


async def test_entity_name_with_numbers(hass: HomeAssistant):
    """Test entity name formatting preserves numbers."""
    hass.states.async_set(
        "binary_sensor.door_sensor_2nd_floor",
        "off",
        {}
    )
    
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Door Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill",
            CONF_SCHEDULE_TYPE: "relative_sensor",
            CONF_RELATIVE_TO_SENSOR: "binary_sensor.door_sensor_2nd_floor",
            CONF_RELATIVE_OFFSET_HOURS: 1,
            CONF_RELATIVE_OFFSET_MINUTES: 0,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
        unique_id="pill_assistant_door_med",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    entity_id = f"sensor.pa_{entry.data[CONF_MEDICATION_NAME].lower().replace(' ', '_')}"
    state = hass.states.get(entity_id)
    
    assert state is not None
    schedule = state.attributes.get("Schedule")
    assert schedule is not None
    # Should format as "Door Sensor 2nd Floor"
    assert "Door Sensor 2nd Floor" in schedule


async def test_entity_name_fallback_when_entity_not_found(hass: HomeAssistant):
    """Test that unknown entity returns formatted name."""
    # Don't create the entity - test fallback behavior
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Unknown Sensor Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill",
            CONF_SCHEDULE_TYPE: "relative_sensor",
            CONF_RELATIVE_TO_SENSOR: "sensor.nonexistent_sensor",
            CONF_RELATIVE_OFFSET_HOURS: 1,
            CONF_RELATIVE_OFFSET_MINUTES: 0,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
        unique_id="pill_assistant_unknown_sensor_med",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    entity_id = f"sensor.pa_{entry.data[CONF_MEDICATION_NAME].lower().replace(' ', '_')}"
    state = hass.states.get(entity_id)
    
    assert state is not None
    schedule = state.attributes.get("Schedule")
    assert schedule is not None
    # Should still format the entity ID even if entity doesn't exist
    assert "Nonexistent Sensor" in schedule


async def test_entity_name_special_characters(hass: HomeAssistant):
    """Test entity name formatting with special characters in entity ID."""
    hass.states.async_set(
        "sensor.co2_sensor_v2",
        "400",
        {"friendly_name": "CO₂ Sensor v2"}
    )
    
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "CO2 Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill",
            CONF_SCHEDULE_TYPE: "relative_sensor",
            CONF_RELATIVE_TO_SENSOR: "sensor.co2_sensor_v2",
            CONF_RELATIVE_OFFSET_HOURS: 0,
            CONF_RELATIVE_OFFSET_MINUTES: 30,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
        unique_id="pill_assistant_co2_med",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    entity_id = f"sensor.pa_{entry.data[CONF_MEDICATION_NAME].lower().replace(' ', '_')}"
    state = hass.states.get(entity_id)
    
    assert state is not None
    schedule = state.attributes.get("Schedule")
    assert schedule is not None
    # Should use friendly name with special characters
    assert "CO₂ Sensor v2" in schedule
