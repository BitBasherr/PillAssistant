"""Test notification action listener deduplication."""

import pytest
from homeassistant.core import HomeAssistant, Event
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
)


@pytest.mark.asyncio
async def test_notification_listeners_registered_once(hass: HomeAssistant):
    """Test that notification action listeners are registered only once globally."""
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
    await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    # Check that listeners are registered
    assert hass.data[DOMAIN].get("notification_listeners_registered") is True

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
    await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    # Verify listeners are still marked as registered (not re-registered)
    assert hass.data[DOMAIN].get("notification_listeners_registered") is True

    # Count the number of listeners for mobile_app_notification_action
    mobile_app_listeners = hass.bus.async_listeners().get(
        "mobile_app_notification_action", 0
    )

    # Should have exactly 1 listener, not 2 (one for each entry)
    assert mobile_app_listeners == 1, f"Expected 1 listener, got {mobile_app_listeners}"


@pytest.mark.asyncio
async def test_notification_action_handler_responds_to_all_medications(
    hass: HomeAssistant,
):
    """Test that notification action handler can handle actions for all medications."""
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

    # Set up both entries
    await hass.config_entries.async_setup(entry1.entry_id)
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

    await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    # Fire notification action event for medication 1
    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": f"take_medication_{entry1.entry_id}"},
    )
    await hass.async_block_till_done()

    # Fire notification action event for medication 2
    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": f"take_medication_{entry2.entry_id}"},
    )
    await hass.async_block_till_done()

    # Verify both medications were taken
    store = hass.data[DOMAIN][entry1.entry_id]["store"]
    storage_data = await store.async_load()

    med1_data = storage_data["medications"][entry1.entry_id]
    med2_data = storage_data["medications"][entry2.entry_id]

    assert med1_data["last_taken"] is not None
    assert med2_data["last_taken"] is not None


@pytest.mark.asyncio
async def test_ios_notification_action_handler(hass: HomeAssistant):
    """Test that iOS notification action events are also handled."""
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

    # Fire iOS notification action event
    hass.bus.async_fire(
        "ios.notification_action_fired",
        {"action": f"snooze_medication_{entry.entry_id}"},
    )
    await hass.async_block_till_done()

    # Verify medication was snoozed
    store = hass.data[DOMAIN][entry.entry_id]["store"]
    storage_data = await store.async_load()

    med_data = storage_data["medications"][entry.entry_id]
    assert med_data.get("snooze_until") is not None


@pytest.mark.asyncio
async def test_notification_action_skip_medication(hass: HomeAssistant):
    """Test that skip action works via notification handler."""
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

    # Fire skip notification action
    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": f"skip_medication_{entry.entry_id}"},
    )
    await hass.async_block_till_done()

    # Verify skip was recorded in history
    store = hass.data[DOMAIN][entry.entry_id]["store"]
    storage_data = await store.async_load()

    history = storage_data.get("history", [])
    assert len(history) == 1
    assert history[0]["action"] == "skipped"
    assert history[0]["medication_id"] == entry.entry_id


@pytest.mark.asyncio
async def test_notification_action_invalid_medication_id(hass: HomeAssistant):
    """Test that invalid medication IDs don't cause errors."""
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

    # Fire notification action with invalid medication ID
    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": "take_medication_invalid_id"},
    )
    await hass.async_block_till_done()

    # Should not raise an error, and storage should be unchanged
    store = hass.data[DOMAIN][entry.entry_id]["store"]
    storage_data = await store.async_load()

    med_data = storage_data["medications"][entry.entry_id]
    assert med_data["last_taken"] is None  # Medication was not taken
