"""Test snooze functionality for Pill Assistant."""

import pytest
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    SERVICE_SNOOZE_MEDICATION,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    ATTR_SNOOZE_UNTIL,
)


async def test_snooze_medication_service(hass: HomeAssistant):
    """Test the snooze medication service."""
    # Create a config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med for Snooze",
            CONF_DOSAGE: "100",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            "notes": "",
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify service is registered
    assert hass.services.has_service(DOMAIN, SERVICE_SNOOZE_MEDICATION)

    # Call the snooze service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SNOOZE_MEDICATION,
        {
            "medication_id": config_entry.entry_id,
            "snooze_duration": 30,  # 30 minutes
        },
        blocking=True,
    )

    await hass.async_block_till_done()
    
    # Verify snooze was stored in storage
    store_data = hass.data[DOMAIN][config_entry.entry_id]
    storage_data = store_data["storage_data"]
    med_data = storage_data["medications"].get(config_entry.entry_id, {})
    snooze_until_str = med_data.get("snooze_until")
    
    assert snooze_until_str is not None, "Snooze should be stored in medication data"
    
    # Verify snooze_until is in the future
    snooze_until = datetime.fromisoformat(snooze_until_str)
    now = dt_util.now()
    assert snooze_until > now
    
    # Verify snooze duration is approximately 30 minutes
    duration_seconds = (snooze_until - now).total_seconds()
    assert 1700 < duration_seconds < 1900  # Allow some tolerance


async def test_snooze_medication_default_duration(hass: HomeAssistant):
    """Test the snooze medication service with default duration."""
    # Create a config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med Default Snooze",
            CONF_DOSAGE: "50",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["12:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            "notes": "",
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Call the snooze service without specifying duration (should use default)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SNOOZE_MEDICATION,
        {"medication_id": config_entry.entry_id},
        blocking=True,
    )

    await hass.async_block_till_done()

    # Verify snooze was stored in storage
    store_data = hass.data[DOMAIN][config_entry.entry_id]
    storage_data = store_data["storage_data"]
    med_data = storage_data["medications"].get(config_entry.entry_id, {})
    snooze_until_str = med_data.get("snooze_until")
    
    assert snooze_until_str is not None, "Snooze should be stored with default duration"


async def test_snooze_prevents_due_state(hass: HomeAssistant):
    """Test that snoozing prevents medication from being marked as due."""
    # Create a config entry with a time that should be "due" soon
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med Snooze State",
            CONF_DOSAGE: "75",
            CONF_DOSAGE_UNIT: "mg",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            "notes": "",
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Snooze the medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SNOOZE_MEDICATION,
        {
            "medication_id": config_entry.entry_id,
            "snooze_duration": 60,
        },
        blocking=True,
    )

    await hass.async_block_till_done()

    # Get the sensor entity
    entity_id = "sensor.test_med_snooze_state"
    state = hass.states.get(entity_id)
    
    assert state is not None
    
    # The state should be "scheduled" even if dose time would normally make it "due"
    # (depends on current time, but snooze should prevent "due" or "overdue" state)
    assert state.state in ["scheduled", "taken", "refill_needed"]
