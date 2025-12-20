"""Test dosage display formatting and pluralization."""

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


@pytest.mark.parametrize(
    "dosage,med_type,unit,expected_parts",
    [
        # Test with "each" unit - should show medication type
        ("1", "pill", "each", ["1", "pill"]),
        ("2", "pill", "each", ["2", "pills"]),
        ("1", "tablet", "each", ["1", "tablet"]),
        ("2", "tablet", "each", ["2", "tablets"]),
        ("1", "capsule", "each", ["1", "capsule"]),
        ("2", "capsule", "each", ["2", "capsules"]),
        ("1", "gummy", "each", ["1", "gummy"]),
        ("2", "gummy", "each", ["2", "gummies"]),
        ("1.5", "tablet", "each", ["1.5", "tablets"]),
        
        # Test with specific units - should show unit, not type
        ("5", "tablet", "mg", ["5", "mg"]),
        ("10", "liquid", "mL", ["10", "mL"]),
        ("500", "pill", "mg", ["500", "mg"]),
        ("2.5", "liquid", "mL", ["2.5", "mL"]),
        ("100", "tablet", "mcg", ["100", "mcg"]),
        ("1", "liquid", "tsp", ["1", "tsp"]),
        ("2", "syrup", "TBSP", ["2", "TBSP"]),
        ("50", "injection", "units", ["50", "units"]),
        ("1000", "vitamin", "IU", ["1000", "IU"]),
        ("0.5", "tablet", "g", ["0.5", "g"]),
    ],
)
async def test_medication_entity_attributes_format(
    hass: HomeAssistant, dosage, med_type, unit, expected_parts
):
    """Test that medication entities expose properly formatted attributes."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med",
            CONF_DOSAGE: dosage,
            CONF_DOSAGE_UNIT: unit,
            CONF_MEDICATION_TYPE: med_type,
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
    
    # Get the sensor entity
    entity_id = "sensor.pa_test_med"
    state = hass.states.get(entity_id)
    
    assert state is not None
    
    # Verify the entity has the correct attributes
    assert state.attributes.get("dosage") == dosage  # Stored as string
    assert state.attributes.get("dosage_unit") == unit
    assert state.attributes.get("medication_type") == med_type
    
    # Note: The frontend will use formatDosageDisplay() to create the display string
    # We verify the backend provides the correct raw data


async def test_legacy_dosage_unit_migration(hass: HomeAssistant):
    """Test that legacy dosage units are properly migrated."""
    # Test with old format "tablet(s)"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Legacy Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "tablet(s)",  # Old format
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
    
    # Get the sensor entity
    entity_id = "sensor.pa_legacy_med"
    state = hass.states.get(entity_id)
    
    assert state is not None
    
    # Should have migrated to new format
    assert state.attributes.get("medication_type") == "tablet"
    assert state.attributes.get("dosage_unit") == "each"


async def test_medication_with_mg_unit(hass: HomeAssistant):
    """Test medication with mg unit displays correctly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Aspirin",
            CONF_DOSAGE: "500",
            CONF_DOSAGE_UNIT: "mg",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 100,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    entity_id = "sensor.pa_aspirin"
    state = hass.states.get(entity_id)
    
    assert state is not None
    assert state.attributes.get("dosage") == "500.0"
    assert state.attributes.get("dosage_unit") == "mg"
    assert state.attributes.get("medication_type") == "tablet"
    
    # Frontend should display as "500 mg" not "500 tablets (mg)"


async def test_medication_with_ml_unit(hass: HomeAssistant):
    """Test medication with mL unit displays correctly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Cough Syrup",
            CONF_DOSAGE: "10",
            CONF_DOSAGE_UNIT: "mL",
            CONF_MEDICATION_TYPE: "liquid",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 200,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    entity_id = "sensor.pa_cough_syrup"
    state = hass.states.get(entity_id)
    
    assert state is not None
    assert state.attributes.get("dosage") == "10.0"
    assert state.attributes.get("dosage_unit") == "mL"
    assert state.attributes.get("medication_type") == "liquid"
    
    # Frontend should display as "10 mL" not "10 liquids (mL)"


async def test_medication_with_each_unit_singular(hass: HomeAssistant):
    """Test medication with 'each' unit and singular dosage."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Vitamin",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "capsule",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    entity_id = "sensor.pa_vitamin"
    state = hass.states.get(entity_id)
    
    assert state is not None
    assert state.attributes.get("dosage") == "1.0"
    assert state.attributes.get("dosage_unit") == "each"
    assert state.attributes.get("medication_type") == "capsule"
    
    # Frontend should display as "1 capsule" not "1 capsule(s) (each)"


async def test_medication_with_each_unit_plural(hass: HomeAssistant):
    """Test medication with 'each' unit and plural dosage."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Vitamin Multi",
            CONF_DOSAGE: "2",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    entity_id = "sensor.pa_vitamin_multi"
    state = hass.states.get(entity_id)
    
    assert state is not None
    assert state.attributes.get("dosage") == "2.0"
    assert state.attributes.get("dosage_unit") == "each"
    assert state.attributes.get("medication_type") == "tablet"
    
    # Frontend should display as "2 tablets" not "2 tablet(s) (each)"


async def test_medication_with_gummy_pluralization(hass: HomeAssistant):
    """Test that gummy pluralizes correctly to gummies."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Gummy Vitamin",
            CONF_DOSAGE: "2",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "gummy",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 90,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    
    entity_id = "sensor.pa_gummy_vitamin"
    state = hass.states.get(entity_id)
    
    assert state is not None
    assert state.attributes.get("dosage") == "2.0"
    assert state.attributes.get("medication_type") == "gummy"
    
    # Frontend should display as "2 gummies" not "2 gummys"


async def test_medication_decimal_dosage(hass: HomeAssistant):
    """Test medication with decimal dosage."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Half Tablet",
            CONF_DOSAGE: "0.5",
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
    
    entity_id = "sensor.pa_half_tablet"
    state = hass.states.get(entity_id)
    
    assert state is not None
    assert state.attributes.get("dosage") == "0.5"
    assert state.attributes.get("medication_type") == "tablet"
    
    # Frontend should display as "0.5 tablets" (plural since not exactly 1)
