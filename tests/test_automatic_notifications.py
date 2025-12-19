"""Test automatic notification feature for Pill Assistant."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_ENABLE_AUTOMATIC_NOTIFICATIONS,
    CONF_MEDICATION_NAME,
    CONF_NOTIFY_SERVICES,
    CONF_ON_TIME_WINDOW_MINUTES,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TIMES,
    DOMAIN,
)


@pytest.fixture
def mock_notify_service():
    """Mock the notify service."""
    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as mock_call:
        yield mock_call


async def test_automatic_notification_config_defaults(hass: HomeAssistant):
    """Test that automatic notification defaults are set correctly."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTIFY_SERVICES: ["notify.mobile_app"],
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check sensor attributes include notification settings
    sensor_state = hass.states.get(f"sensor.pa_test_med")
    assert sensor_state is not None
    assert sensor_state.attributes.get("Automatic notifications enabled") is True
    assert sensor_state.attributes.get("On-time window (minutes)") == 30


async def test_automatic_notification_disabled(hass: HomeAssistant, mock_notify_service):
    """Test that automatic notifications can be disabled."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med No Notify",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ENABLE_AUTOMATIC_NOTIFICATIONS: False,
            CONF_NOTIFY_SERVICES: ["notify.mobile_app"],
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify notification is disabled in attributes
    sensor_state = hass.states.get(f"sensor.pa_test_med_no_notify")
    assert sensor_state is not None
    assert sensor_state.attributes.get("Automatic notifications enabled") is False

    # No notification should be sent even if medication becomes due
    # (we can't easily simulate time-based triggering in tests, but we verify the config)
    mock_notify_service.assert_not_called()


async def test_on_time_window_custom_value(hass: HomeAssistant):
    """Test that custom on-time window values are stored and exposed."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med Custom Window",
            CONF_DOSAGE: "2",
            CONF_DOSAGE_UNIT: "tablet(s)",
            CONF_SCHEDULE_TIMES: ["09:00", "21:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 5,
            CONF_ON_TIME_WINDOW_MINUTES: 15,  # Custom 15-minute window
            CONF_ENABLE_AUTOMATIC_NOTIFICATIONS: True,
            CONF_NOTIFY_SERVICES: ["notify.telegram"],
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify custom window is stored
    sensor_state = hass.states.get(f"sensor.pa_test_med_custom_window")
    assert sensor_state is not None
    assert sensor_state.attributes.get("On-time window (minutes)") == 15
    assert sensor_state.attributes.get("Automatic notifications enabled") is True


async def test_notification_service_configuration(hass: HomeAssistant):
    """Test that notification services are properly configured."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Multi Notify Med",
            CONF_DOSAGE: "5",
            CONF_DOSAGE_UNIT: "mL",
            CONF_SCHEDULE_TIMES: ["07:00"],
            CONF_SCHEDULE_DAYS: ["mon", "wed", "fri"],
            CONF_REFILL_AMOUNT: 20,
            CONF_REFILL_REMINDER_DAYS: 3,
            CONF_ENABLE_AUTOMATIC_NOTIFICATIONS: True,
            CONF_NOTIFY_SERVICES: ["notify.mobile_app", "notify.telegram"],
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify the entry has notification services configured
    assert config_entry.data[CONF_NOTIFY_SERVICES] == [
        "notify.mobile_app",
        "notify.telegram",
    ]


async def test_automatic_notification_no_services(hass: HomeAssistant):
    """Test graceful handling when no notification services are configured."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "No Service Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["10:00"],
            CONF_SCHEDULE_DAYS: ["tue", "thu", "sat"],
            CONF_REFILL_AMOUNT: 15,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ENABLE_AUTOMATIC_NOTIFICATIONS: True,
            # No CONF_NOTIFY_SERVICES specified
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Should still work without notification services
    sensor_state = hass.states.get(f"sensor.pa_no_service_med")
    assert sensor_state is not None


async def test_on_time_window_zero(hass: HomeAssistant):
    """Test that on-time window can be set to 0 (exact time only)."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Exact Time Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["12:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ON_TIME_WINDOW_MINUTES: 0,  # Exact time only
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    sensor_state = hass.states.get(f"sensor.pa_exact_time_med")
    assert sensor_state is not None
    assert sensor_state.attributes.get("On-time window (minutes)") == 0
