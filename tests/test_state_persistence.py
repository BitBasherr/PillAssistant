"""Test state persistence across restarts."""

import pytest
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_MEDICATION_TYPE,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    SERVICE_TAKE_MEDICATION,
    ATTR_MEDICATION_ID,
    STORAGE_KEY,
    STORAGE_VERSION,
)


@pytest.mark.asyncio
async def test_state_persists_after_reload(hass: HomeAssistant):
    """Test that medication state persists after reloading the integration."""
    # Create a medication entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "2",
            CONF_MEDICATION_TYPE: "pill",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)

    # Set up the integration
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Take the medication to create state
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get the storage data
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    storage_data = await store.async_load()

    # Verify state was saved
    med_id = entry.entry_id
    assert med_id in storage_data["medications"]
    med_data = storage_data["medications"][med_id]
    assert med_data["last_taken"] is not None
    assert med_data["remaining_amount"] == 29  # Started with 30 doses, took 1 dose

    # Store the last_taken value
    last_taken_before = med_data["last_taken"]
    remaining_before = med_data["remaining_amount"]

    # Unload the integration
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Reload the integration
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify state persisted
    storage_data_after = await store.async_load()
    med_data_after = storage_data_after["medications"][med_id]
    assert med_data_after["last_taken"] == last_taken_before
    assert med_data_after["remaining_amount"] == remaining_before


@pytest.mark.asyncio
async def test_relative_medication_state_persists(hass: HomeAssistant):
    """Test that relative medication scheduling state persists."""
    # Create first medication
    entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med A",
            CONF_DOSAGE: "1",
            CONF_MEDICATION_TYPE: "pill",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry1.add_to_hass(hass)

    # Set up first medication
    await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    # Take the first medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry1.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get storage and verify state
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    storage_data = await store.async_load()
    last_taken_med1 = storage_data["medications"][entry1.entry_id]["last_taken"]
    assert last_taken_med1 is not None

    # Unload and reload
    await hass.config_entries.async_unload(entry1.entry_id)
    await hass.async_block_till_done()
    await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    # Verify state persisted
    storage_data_after = await store.async_load()
    assert (
        storage_data_after["medications"][entry1.entry_id]["last_taken"]
        == last_taken_med1
    )


@pytest.mark.asyncio
async def test_snooze_state_persists(hass: HomeAssistant):
    """Test that snooze state persists across reloads."""
    from custom_components.pill_assistant.const import SERVICE_SNOOZE_MEDICATION

    # Create a medication entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_MEDICATION_TYPE: "pill",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)

    # Set up the integration
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Snooze the medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SNOOZE_MEDICATION,
        {ATTR_MEDICATION_ID: entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get the storage data
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    storage_data = await store.async_load()
    snooze_until_before = storage_data["medications"][entry.entry_id].get(
        "snooze_until"
    )
    assert snooze_until_before is not None

    # Unload and reload
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify snooze state persisted
    storage_data_after = await store.async_load()
    snooze_until_after = storage_data_after["medications"][entry.entry_id].get(
        "snooze_until"
    )
    assert snooze_until_after == snooze_until_before


@pytest.mark.asyncio
async def test_missed_doses_persist(hass: HomeAssistant):
    """Test that missed doses information persists."""
    from homeassistant.util import dt as dt_util
    from unittest.mock import patch

    # Create a medication entry with a past schedule time
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: "1",
            CONF_MEDICATION_TYPE: "pill",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)

    # Mock current time to be after the scheduled time
    now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    with patch("homeassistant.util.dt.now", return_value=now):
        # Set up the integration
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Let the sensor update to detect missed doses
        await hass.async_block_till_done()

        # Get the storage data
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        storage_data = await store.async_load()

        # Store missed doses count
        missed_doses_before = storage_data["medications"][entry.entry_id].get(
            "missed_doses", []
        )

        # Unload and reload
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Verify missed doses persisted
        storage_data_after = await store.async_load()
        missed_doses_after = storage_data_after["medications"][entry.entry_id].get(
            "missed_doses", []
        )
        assert missed_doses_after == missed_doses_before
