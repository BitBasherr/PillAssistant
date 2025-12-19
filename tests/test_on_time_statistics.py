"""Test on-time statistics for Pill Assistant."""

from datetime import datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    ATTR_MEDICATION_ID,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_MEDICATION_NAME,
    CONF_ON_TIME_WINDOW_MINUTES,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TIMES,
    DOMAIN,
    SERVICE_GET_STATISTICS,
    SERVICE_TAKE_MEDICATION,
)


async def test_on_time_window_configuration(hass: HomeAssistant):
    """Test that on-time window configuration is properly stored and exposed."""
    # Create medication with custom on-time window
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med Window",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ON_TIME_WINDOW_MINUTES: 45,  # Custom 45-minute window
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify window is stored in config
    assert config_entry.data[CONF_ON_TIME_WINDOW_MINUTES] == 45

    # Verify it's exposed in sensor attributes
    sensor_state = hass.states.get(f"sensor.pa_test_med_window")
    assert sensor_state is not None
    assert sensor_state.attributes.get("On-time window (minutes)") == 45


async def test_statistics_service_exists(hass: HomeAssistant):
    """Test that the statistics service is registered and callable."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med Stats",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ON_TIME_WINDOW_MINUTES: 30,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify service exists
    assert hass.services.has_service(DOMAIN, SERVICE_GET_STATISTICS)

    # Call statistics service (should not raise an error)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {ATTR_MEDICATION_ID: config_entry.entry_id},
        blocking=True,
    )


async def test_on_time_window_defaults(hass: HomeAssistant):
    """Test that on-time window defaults to 30 minutes when not specified."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Default Window Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["09:00"],
            CONF_SCHEDULE_DAYS: ["mon", "wed", "fri"],
            CONF_REFILL_AMOUNT: 15,
            CONF_REFILL_REMINDER_DAYS: 5,
            # CONF_ON_TIME_WINDOW_MINUTES not specified
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify default value
    sensor_state = hass.states.get(f"sensor.pa_default_window_med")
    assert sensor_state is not None
    # Should default to 30 minutes
    assert sensor_state.attributes.get("On-time window (minutes)") == 30


async def test_multiple_medications_different_windows(hass: HomeAssistant):
    """Test that different medications can have different on-time windows."""
    config_entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med 15min",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "wed", "fri"],
            CONF_REFILL_AMOUNT: 15,
            CONF_REFILL_REMINDER_DAYS: 5,
            CONF_ON_TIME_WINDOW_MINUTES: 15,
        },
    )
    config_entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med 60min",
            CONF_DOSAGE: "2",
            CONF_DOSAGE_UNIT: "tablet(s)",
            CONF_SCHEDULE_TIMES: ["09:00"],
            CONF_SCHEDULE_DAYS: ["tue", "thu", "sat"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ON_TIME_WINDOW_MINUTES: 60,
        },
    )

    config_entry1.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry1.entry_id)
    await hass.async_block_till_done()

    config_entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry2.entry_id)
    await hass.async_block_till_done()

    # Verify each has its own window
    sensor1 = hass.states.get(f"sensor.pa_med_15min")
    sensor2 = hass.states.get(f"sensor.pa_med_60min")

    assert sensor1 is not None
    assert sensor2 is not None
    assert sensor1.attributes.get("On-time window (minutes)") == 15
    assert sensor2.attributes.get("On-time window (minutes)") == 60


async def test_on_time_window_zero_value(hass: HomeAssistant):
    """Test that on-time window can be set to 0 (exact time required)."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Exact Time Required",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["12:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ON_TIME_WINDOW_MINUTES: 0,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    sensor_state = hass.states.get(f"sensor.pa_exact_time_required")
    assert sensor_state is not None
    assert sensor_state.attributes.get("On-time window (minutes)") == 0


async def test_on_time_window_large_value(hass: HomeAssistant):
    """Test that on-time window can be set to a large value."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Flexible Schedule",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["10:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ON_TIME_WINDOW_MINUTES: 180,  # 3-hour window
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    sensor_state = hass.states.get(f"sensor.pa_flexible_schedule")
    assert sensor_state is not None
    assert sensor_state.attributes.get("On-time window (minutes)") == 180
