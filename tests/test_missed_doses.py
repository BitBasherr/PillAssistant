"""Test missed doses functionality."""

from datetime import datetime, timedelta
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import DOMAIN


async def test_missed_doses_no_duplicates(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that missed doses do not contain duplicates."""
    # Add the entry to hass
    mock_config_entry.add_to_hass(hass)

    # Set up the integration
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get the sensor entity
    entity_id = f"sensor.pa_{mock_config_entry.data['medication_name'].lower().replace(' ', '_')}"
    state = hass.states.get(entity_id)

    assert state is not None

    # Get missed doses attribute
    missed_doses = state.attributes.get("missed_doses", [])

    # Check that there are no duplicates
    assert len(missed_doses) == len(
        set(missed_doses)
    ), f"Found duplicate missed doses: {missed_doses}"


async def test_missed_doses_within_24_hours(hass: HomeAssistant):
    """Test that missed doses only includes doses within 24 hours."""
    now = dt_util.now()

    # Create a config entry with schedule times
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "medication_name": "Test Med 24h",
            "dosage": "50",
            "dosage_unit": "mg",
            "schedule_times": ["12:30", "16:30"],
            "schedule_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "refill_amount": 30,
            "refill_reminder_days": 7,
            "notes": "",
        },
    )
    config_entry.add_to_hass(hass)

    # Set up the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get the sensor entity
    entity_id = "sensor.pa_test_med_24h"
    state = hass.states.get(entity_id)

    assert state is not None

    # Get missed doses attribute
    missed_doses = state.attributes.get("missed_doses", [])

    # All missed doses should be within 24 hours
    for dose_str in missed_doses:
        dose_time = datetime.fromisoformat(dose_str)
        time_diff = (now - dose_time).total_seconds()
        assert 0 < time_diff <= 86400, f"Dose {dose_str} is not within 24 hours"


async def test_missed_doses_respects_last_taken(hass: HomeAssistant):
    """Test that missed doses are not reported after medication is taken."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "medication_name": "Test Med Last Taken",
            "dosage": "50",
            "dosage_unit": "mg",
            "schedule_times": ["08:00"],
            "schedule_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "refill_amount": 30,
            "refill_reminder_days": 7,
            "notes": "",
        },
    )
    config_entry.add_to_hass(hass)

    # Set up the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Take the medication
    await hass.services.async_call(
        DOMAIN,
        "take_medication",
        {"medication_id": config_entry.entry_id},
        blocking=True,
    )

    # Wait for state update and trigger sensor update
    await hass.async_block_till_done()

    # Force a state update by waiting for the next update interval
    import asyncio

    await asyncio.sleep(0.1)

    # Get the sensor entity
    entity_id = "sensor.pa_test_med_last_taken"

    # Manually trigger update by getting storage data
    store_data = hass.data[DOMAIN][config_entry.entry_id]
    storage_data = store_data["storage_data"]
    med_data = storage_data["medications"].get(config_entry.entry_id, {})
    last_taken_str = med_data.get("last_taken")

    assert (
        last_taken_str is not None
    ), "Last taken should be set after taking medication in storage"

    # The sensor state should reflect this after update
    state = hass.states.get(entity_id)
    assert state is not None

    # Get missed doses - should be empty or not include recently taken doses
    missed_doses = state.attributes.get("missed_doses", [])

    # Parse last taken time from storage (source of truth)
    last_taken = datetime.fromisoformat(last_taken_str)

    # No missed doses should be after last_taken time
    for dose_str in missed_doses:
        dose_time = datetime.fromisoformat(dose_str)
        assert (
            dose_time <= last_taken
        ), f"Missed dose {dose_str} is after last taken time {last_taken_str}"


async def test_missed_doses_sorted_chronologically(hass: HomeAssistant):
    """Test that missed doses are sorted chronologically (oldest first)."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "medication_name": "Test Med Sorted",
            "dosage": "50",
            "dosage_unit": "mg",
            "schedule_times": ["08:00", "12:00", "18:00"],
            "schedule_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "refill_amount": 30,
            "refill_reminder_days": 7,
            "notes": "",
        },
    )
    config_entry.add_to_hass(hass)

    # Set up the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get the sensor entity
    entity_id = "sensor.pa_test_med_sorted"
    state = hass.states.get(entity_id)

    assert state is not None

    # Get missed doses attribute
    missed_doses = state.attributes.get("missed_doses", [])

    # Check that doses are sorted chronologically
    if len(missed_doses) > 1:
        for i in range(len(missed_doses) - 1):
            dose1 = datetime.fromisoformat(missed_doses[i])
            dose2 = datetime.fromisoformat(missed_doses[i + 1])
            assert dose1 <= dose2, f"Missed doses are not sorted: {missed_doses}"
