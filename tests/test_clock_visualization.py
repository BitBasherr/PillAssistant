"""Test clock visualization data and time formatting."""

from datetime import timedelta
import os

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    ATTR_END_DATE,
    ATTR_MEDICATION_ID,
    ATTR_START_DATE,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_MEDICATION_NAME,
    CONF_MEDICATION_TYPE,
    CONF_ON_TIME_WINDOW_MINUTES,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_TYPE,
    CONF_RELATIVE_TO_SENSOR,
    CONF_RELATIVE_OFFSET_HOURS,
    CONF_RELATIVE_OFFSET_MINUTES,
    DOMAIN,
    SERVICE_GET_STATISTICS,
    SERVICE_TAKE_MEDICATION,
    SERVICE_SKIP_MEDICATION,
    SERVICE_SNOOZE_MEDICATION,
)


async def test_statistics_includes_taken_times(hass: HomeAssistant):
    """Test that statistics response includes taken_times array for clock visualization."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Clock Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "pill",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ON_TIME_WINDOW_MINUTES: 30,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Take medication multiple times
    for _ in range(3):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TAKE_MEDICATION,
            {ATTR_MEDICATION_ID: config_entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Get statistics
    now = dt_util.now()
    start_date = (now - timedelta(days=1)).isoformat()
    end_date = now.isoformat()

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: start_date,
            ATTR_END_DATE: end_date,
        },
        blocking=True,
        return_response=True,
    )

    # Verify response includes taken_times array
    assert response is not None
    assert "medications" in response
    assert config_entry.entry_id in response["medications"]

    med_stats = response["medications"][config_entry.entry_id]
    assert "taken_times" in med_stats
    assert isinstance(med_stats["taken_times"], list)
    assert len(med_stats["taken_times"]) == 3  # We took medication 3 times


async def test_statistics_includes_skipped_times(hass: HomeAssistant):
    """Test that statistics response includes skipped_times array for clock visualization."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Skip Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "pill",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["09:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Skip medication twice
    for _ in range(2):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SKIP_MEDICATION,
            {ATTR_MEDICATION_ID: config_entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Get statistics
    now = dt_util.now()
    start_date = (now - timedelta(days=1)).isoformat()
    end_date = now.isoformat()

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: start_date,
            ATTR_END_DATE: end_date,
        },
        blocking=True,
        return_response=True,
    )

    # Verify response includes skipped_times array
    assert response is not None
    assert "medications" in response
    assert config_entry.entry_id in response["medications"]

    med_stats = response["medications"][config_entry.entry_id]
    assert "skipped_times" in med_stats
    assert isinstance(med_stats["skipped_times"], list)
    assert len(med_stats["skipped_times"]) == 2


async def test_statistics_includes_snoozed_times(hass: HomeAssistant):
    """Test that statistics response includes snoozed_times array for clock visualization."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Snooze Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "pill",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["10:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Snooze medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SNOOZE_MEDICATION,
        {ATTR_MEDICATION_ID: config_entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get statistics
    now = dt_util.now()
    start_date = (now - timedelta(days=1)).isoformat()
    end_date = now.isoformat()

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: start_date,
            ATTR_END_DATE: end_date,
        },
        blocking=True,
        return_response=True,
    )

    # Verify response includes snoozed_times array (even if empty, it should exist)
    assert response is not None
    assert "medications" in response
    assert config_entry.entry_id in response["medications"]

    med_stats = response["medications"][config_entry.entry_id]
    assert "snoozed_times" in med_stats
    assert isinstance(med_stats["snoozed_times"], list)


async def test_html_panel_contains_clock_toggle(hass: HomeAssistant):
    """Test that the HTML panel contains 24-hour clock toggle."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for 24-hour clock toggle checkbox
    assert "show-24hr-clock" in content, "24-hour clock toggle checkbox missing"
    assert "toggle24HourClock" in content, "toggle24HourClock function missing"
    assert "Show 24-Hour Clock" in content, "24-hour clock label missing"

    # Check that 24-hour clock wrapper is hidden by default
    assert 'id="clock-24hr-wrapper"' in content, "24-hour clock wrapper missing"
    assert 'style="display: none;"' in content, "24-hour clock should be hidden by default"


async def test_html_panel_local_date_function(hass: HomeAssistant):
    """Test that the HTML panel uses local date function instead of toISOString."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for local date string function
    assert "getLocalDateString" in content, "getLocalDateString function missing"
    assert "getFullYear()" in content, "Local year extraction missing"
    assert "getMonth()" in content, "Local month extraction missing"
    assert "getDate()" in content, "Local date extraction missing"


async def test_html_panel_scatter_plot_support(hass: HomeAssistant):
    """Test that the HTML panel supports scatter plot chart type."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for scatter plot support
    assert "type: 'scatter'" in content or "type: chartType" in content, "Scatter chart type missing"
    assert "isScatterPlot" in content, "Scatter plot detection variable missing"
    assert "pointRadius" in content, "Point radius for scatter missing"


async def test_html_panel_days_formatting(hass: HomeAssistant):
    """Test that the HTML panel properly formats days of the week."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for days formatting
    assert "dayMappings" in content, "Day mappings object missing"
    assert "'mon': 'Mon'" in content, "Monday mapping missing"
    assert "'tue': 'Tue'" in content, "Tuesday mapping missing"
    assert "'wed': 'Wed'" in content, "Wednesday mapping missing"
    assert "Daily" in content, "Daily schedule shortcut missing"


async def test_time_offset_format_readable(hass: HomeAssistant):
    """Test that relative schedule time offset is human-readable."""
    # Create a sensor for reference
    hass.states.async_set("sensor.test_sensor", "on")
    
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Offset Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "pill",
            CONF_SCHEDULE_TYPE: "relative_sensor",
            CONF_RELATIVE_TO_SENSOR: "sensor.test_sensor",
            CONF_RELATIVE_OFFSET_HOURS: 0,
            CONF_RELATIVE_OFFSET_MINUTES: 15,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get the sensor state
    state = hass.states.get("sensor.pa_offset_test_med")
    assert state is not None

    # Check schedule attribute is readable format (not "0h 15m")
    schedule = state.attributes.get("Schedule", "")
    # Should contain "15 min" not "0h 15m"
    assert "15 min" in schedule, f"Schedule should use readable format, got: {schedule}"
    assert "0h" not in schedule, f"Schedule should not use 0h format, got: {schedule}"


async def test_time_offset_format_hours_only(hass: HomeAssistant):
    """Test that time offset with only hours is formatted correctly."""
    hass.states.async_set("sensor.test_sensor2", "on")
    
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Hours Only Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "pill",
            CONF_SCHEDULE_TYPE: "relative_sensor",
            CONF_RELATIVE_TO_SENSOR: "sensor.test_sensor2",
            CONF_RELATIVE_OFFSET_HOURS: 2,
            CONF_RELATIVE_OFFSET_MINUTES: 0,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.pa_hours_only_med")
    assert state is not None

    schedule = state.attributes.get("Schedule", "")
    # Should contain "2 hrs" not "2h 0m"
    assert "2 hrs" in schedule, f"Schedule should use readable format, got: {schedule}"
    assert "0m" not in schedule, f"Schedule should not show 0m, got: {schedule}"


async def test_time_offset_format_mixed(hass: HomeAssistant):
    """Test that time offset with both hours and minutes is formatted correctly."""
    hass.states.async_set("sensor.test_sensor3", "on")
    
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Mixed Time Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "pill",
            CONF_SCHEDULE_TYPE: "relative_sensor",
            CONF_RELATIVE_TO_SENSOR: "sensor.test_sensor3",
            CONF_RELATIVE_OFFSET_HOURS: 1,
            CONF_RELATIVE_OFFSET_MINUTES: 30,
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.pa_mixed_time_med")
    assert state is not None

    schedule = state.attributes.get("Schedule", "")
    # Should contain "1 hr 30 min" not "1h 30m"
    assert "1 hr" in schedule, f"Schedule should use readable format, got: {schedule}"
    assert "30 min" in schedule, f"Schedule should use readable format, got: {schedule}"
