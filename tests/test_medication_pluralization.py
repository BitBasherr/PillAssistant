"""Test medication type pluralization for Pill Assistant."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_MEDICATION_TYPE,
    CONF_SCHEDULE_TYPE,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
)


async def test_medication_type_singular(hass: HomeAssistant):
    """Test that medication type is singular when dosage is 1."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Single Pill",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "mg",
            CONF_MEDICATION_TYPE: "pill",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.pa_single_pill"
    state = hass.states.get(entity_id)

    assert state is not None
    dosage_display = state.attributes.get("Dosage")
    # Should be "1 pill (mg)" not "1 pills (mg)"
    assert "pill" in dosage_display
    assert "1 pill" in dosage_display


async def test_medication_type_plural(hass: HomeAssistant):
    """Test that medication type is plural when dosage is greater than 1."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Multiple Pills",
            CONF_DOSAGE: "2",
            CONF_DOSAGE_UNIT: "mg",
            CONF_MEDICATION_TYPE: "pill",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.pa_multiple_pills"
    state = hass.states.get(entity_id)

    assert state is not None
    dosage_display = state.attributes.get("Dosage")
    # Should be "2 pills (mg)" not "2 pill (mg)"
    assert "pills" in dosage_display
    assert "2 pills" in dosage_display


async def test_medication_type_gummy_plural(hass: HomeAssistant):
    """Test that gummy pluralizes correctly to gummies."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Gummy Vitamins",
            CONF_DOSAGE: "3",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "gummy",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.pa_gummy_vitamins"
    state = hass.states.get(entity_id)

    assert state is not None
    dosage_display = state.attributes.get("Dosage")
    # Should be "3 gummies (each)" not "3 gummys (each)" or "3 gummy(s) (each)"
    assert "gummies" in dosage_display
    assert "3 gummies" in dosage_display
    # Should not have the old format
    assert "(s)" not in dosage_display


async def test_medication_type_capsule_plural(hass: HomeAssistant):
    """Test that capsule pluralizes correctly to capsules."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Capsule Med",
            CONF_DOSAGE: "2",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "capsule",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.pa_capsule_med"
    state = hass.states.get(entity_id)

    assert state is not None
    dosage_display = state.attributes.get("Dosage")
    # Should be "2 capsules (each)" not "2 capsule(s) (each)"
    assert "capsules" in dosage_display
    assert "2 capsules" in dosage_display
    assert "(s)" not in dosage_display


async def test_medication_type_tablet_plural(hass: HomeAssistant):
    """Test that tablet pluralizes correctly to tablets."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Tablet Med",
            CONF_DOSAGE: "1.5",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.pa_tablet_med"
    state = hass.states.get(entity_id)

    assert state is not None
    dosage_display = state.attributes.get("Dosage")
    # Should be "1.5 tablets (each)" not "1.5 tablet(s) (each)"
    assert "tablets" in dosage_display
    assert "1.5 tablets" in dosage_display
    assert "(s)" not in dosage_display


async def test_medication_type_patch_plural(hass: HomeAssistant):
    """Test that patch pluralizes correctly to patches."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Patch Med",
            CONF_DOSAGE: "2",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "patch",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.pa_patch_med"
    state = hass.states.get(entity_id)

    assert state is not None
    dosage_display = state.attributes.get("Dosage")
    # Should be "2 patches (each)" not "2 patchs (each)"
    assert "patches" in dosage_display
    assert "2 patches" in dosage_display
    assert "(s)" not in dosage_display
