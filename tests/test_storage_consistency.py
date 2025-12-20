"""Test storage consistency with multiple medications."""

import pytest
from homeassistant.core import HomeAssistant
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
)
from custom_components.pill_assistant.store import PillAssistantStore


@pytest.mark.asyncio
async def test_storage_singleton_shared_across_entries(hass: HomeAssistant):
    """Test that all config entries share the same storage singleton."""
    # Create first medication entry
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

    # Set up first entry
    assert await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    # Create second medication entry
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med B",
            CONF_DOSAGE: "2",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TIMES: ["20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry2.add_to_hass(hass)
    
    # Set up second entry
    assert await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    # Verify both entries use the same store instance
    store1 = hass.data[DOMAIN][entry1.entry_id]["store"]
    store2 = hass.data[DOMAIN][entry2.entry_id]["store"]
    
    assert store1 is store2, "Both entries should share the same storage singleton"


@pytest.mark.asyncio
async def test_concurrent_medication_updates_no_data_loss(hass: HomeAssistant):
    """Test that concurrent updates to different medications don't cause data loss."""
    # Create two medication entries
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

    # Set up first entry
    assert await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med B",
            CONF_DOSAGE: "2",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TIMES: ["20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry2.add_to_hass(hass)

    # Set up second entry
    assert await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    # Take medication A
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry1.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Take medication B
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry2.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Reload storage and verify both medications are still present
    store = hass.data[DOMAIN][entry1.entry_id]["store"]
    storage_data = await store.async_load()

    assert entry1.entry_id in storage_data["medications"]
    assert entry2.entry_id in storage_data["medications"]
    
    # Verify both medications have been taken
    med1_data = storage_data["medications"][entry1.entry_id]
    med2_data = storage_data["medications"][entry2.entry_id]
    
    assert med1_data["last_taken"] is not None
    assert med2_data["last_taken"] is not None
    assert med1_data["remaining_amount"] == 29  # Started with 30, took 1
    assert med2_data["remaining_amount"] == 59  # Started with 60, took 1


@pytest.mark.asyncio
async def test_sequential_updates_maintain_consistency(hass: HomeAssistant):
    """Test that sequential updates maintain data consistency."""
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

    # Set up first entry
    assert await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    # Take medication from first entry
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry1.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med B",
            CONF_DOSAGE: "2",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TIMES: ["20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry2.add_to_hass(hass)

    # Set up second entry
    assert await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    # Take medication from second entry
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry2.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify storage contains both medications with correct data
    store = hass.data[DOMAIN][entry1.entry_id]["store"]
    storage_data = await store.async_load()

    assert entry1.entry_id in storage_data["medications"]
    assert entry2.entry_id in storage_data["medications"]
    
    med1_data = storage_data["medications"][entry1.entry_id]
    med2_data = storage_data["medications"][entry2.entry_id]
    
    # Med A was added first and taken once
    assert med1_data["last_taken"] is not None
    assert med1_data["remaining_amount"] == 29
    
    # Med B was added second and taken once
    assert med2_data["last_taken"] is not None
    assert med2_data["remaining_amount"] == 59


@pytest.mark.asyncio
async def test_storage_reset_between_tests(hass: HomeAssistant):
    """Test that storage singleton is properly reset between tests."""
    # Reset the singleton to ensure clean state
    PillAssistantStore.reset_instance()
    
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

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    storage_data = await store.async_load()

    # Should only have one medication
    assert len(storage_data["medications"]) == 1
    assert entry.entry_id in storage_data["medications"]


@pytest.mark.asyncio
async def test_multiple_medications_share_history(hass: HomeAssistant):
    """Test that multiple medications share the same history list."""
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

    assert await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med B",
            CONF_DOSAGE: "2",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TIMES: ["20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry2.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    # Take both medications
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry1.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry2.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify history contains entries for both medications
    store = hass.data[DOMAIN][entry1.entry_id]["store"]
    storage_data = await store.async_load()

    assert len(storage_data["history"]) == 2
    
    # Check that both medications are in history
    med_ids_in_history = {entry["medication_id"] for entry in storage_data["history"]}
    assert entry1.entry_id in med_ids_in_history
    assert entry2.entry_id in med_ids_in_history
