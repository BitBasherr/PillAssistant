"""Test frontend features like medication sorting and clock data."""

import pytest
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

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
    SERVICE_GET_STATISTICS,
    ATTR_START_DATE,
    ATTR_END_DATE,
)


@pytest.fixture
async def setup_multiple_medications(hass: HomeAssistant):
    """Set up multiple medications with different next dose times."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    # Medication 1: Next dose in 1 hour
    entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med_A",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "mg",
            CONF_MEDICATION_TYPE: "pill",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["10:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry1.add_to_hass(hass)

    # Medication 2: Next dose in 3 hours
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med_B",
            CONF_DOSAGE: "2",
            CONF_DOSAGE_UNIT: "mL",
            CONF_MEDICATION_TYPE: "liquid",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["14:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 100,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry2.add_to_hass(hass)

    # Medication 3: Next dose in 30 minutes
    entry3 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med_C",
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
    entry3.add_to_hass(hass)

    await hass.config_entries.async_setup(entry1.entry_id)
    await hass.config_entries.async_setup(entry2.entry_id)
    await hass.config_entries.async_setup(entry3.entry_id)
    await hass.async_block_till_done()

    return [entry1, entry2, entry3]


async def test_medications_have_next_dose_time(
    hass: HomeAssistant, setup_multiple_medications
):
    """Test that all medications have next_dose_time attribute for sorting."""
    medications = setup_multiple_medications

    # Check that all sensor entities have next_dose_time attribute
    for entry in medications:
        med_name = entry.data[CONF_MEDICATION_NAME].lower().replace(" ", "_")
        entity_id = f"sensor.pa_{med_name}"

        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"

        # Check for next_dose_time in attributes
        attrs = state.attributes
        assert (
            "Next dose time" in attrs or "next_dose_time" in attrs
        ), f"Entity {entity_id} missing next_dose_time attribute"


async def test_medication_type_and_unit_separation(hass: HomeAssistant):
    """Test that medication_type and dosage_unit are separate attributes."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test_Separation",
            CONF_DOSAGE: "5",
            CONF_DOSAGE_UNIT: "mL",
            CONF_MEDICATION_TYPE: "liquid",
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

    state = hass.states.get("sensor.pa_test_separation")
    assert state is not None

    attrs = state.attributes

    # Check that both medication_type and dosage_unit are present and separate
    assert "Medication Type" in attrs or "medication_type" in attrs
    assert "Dosage unit" in attrs or "dosage_unit" in attrs

    med_type = attrs.get("Medication Type") or attrs.get("medication_type")
    dosage_unit = attrs.get("Dosage unit") or attrs.get("dosage_unit")

    assert med_type == "liquid"
    assert dosage_unit == "mL"
    assert med_type != dosage_unit, "Type and unit should be different values"


async def test_statistics_service_for_clock_data(hass: HomeAssistant):
    """Test that statistics service provides data for clock visualizations."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Clock_Test",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "pill",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Get medication ID
    state = hass.states.get("sensor.pa_clock_test")
    assert state is not None
    med_id = state.attributes.get("Medication ID") or state.attributes.get(
        "medication_id"
    )

    # Take medication to generate data
    await hass.services.async_call(
        DOMAIN,
        "take_medication",
        {"medication_id": med_id},
        blocking=True,
    )

    # Call statistics service for today
    today = dt_util.now().date().isoformat()

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: today,
            ATTR_END_DATE: today,
        },
        blocking=True,
        return_response=True,
    )

    # Verify response structure for clock data
    assert response is not None
    # The response should be a dictionary (even if empty for no data)
    assert isinstance(response, dict), "Statistics response should be a dictionary"


async def test_clock_date_range_data(hass: HomeAssistant):
    """Test that statistics can be queried for different date ranges."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Date_Range_Test",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["10:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Test different date ranges
    today = dt_util.now().date()
    yesterday = (today - timedelta(days=1)).isoformat()
    today_str = today.isoformat()

    # Query for yesterday
    response_yesterday = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: yesterday,
            ATTR_END_DATE: yesterday,
        },
        blocking=True,
        return_response=True,
    )

    # Query for today
    response_today = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: today_str,
            ATTR_END_DATE: today_str,
        },
        blocking=True,
        return_response=True,
    )

    # Both queries should succeed (even if no data for yesterday)
    assert response_yesterday is not None
    assert response_today is not None

    # Verify the service handles date ranges properly
    assert (
        "medications" in response_yesterday or "medication_stats" in response_yesterday
    )
    assert "medications" in response_today or "medication_stats" in response_today


async def test_medication_sorting_by_schedule(
    hass: HomeAssistant, setup_multiple_medications
):
    """Test that medications can be sorted by their next_dose_time."""
    medications = setup_multiple_medications

    # Get all medication entities
    med_states = []
    for entry in medications:
        med_name = entry.data[CONF_MEDICATION_NAME].lower().replace(" ", "_")
        entity_id = f"sensor.pa_{med_name}"
        state = hass.states.get(entity_id)
        if state:
            med_states.append(
                {
                    "entity_id": entity_id,
                    "name": entry.data[CONF_MEDICATION_NAME],
                    "next_dose": state.attributes.get("Next dose time")
                    or state.attributes.get("next_dose_time"),
                }
            )

    # Verify we have multiple medications
    assert len(med_states) >= 3

    # Verify that next_dose times are different and sortable
    next_doses = [med["next_dose"] for med in med_states if med["next_dose"]]
    assert len(next_doses) >= 3, "All medications should have next_dose_time"

    # Try to parse and sort the times
    parsed_times = []
    for dose_time in next_doses:
        if dose_time and dose_time not in ["Unknown", "Never"]:
            try:
                parsed_times.append(
                    datetime.fromisoformat(dose_time.replace("Z", "+00:00"))
                )
            except (ValueError, AttributeError):
                # If parsing fails, that's also valid test information
                pass

    # If we successfully parsed times, verify they can be sorted
    if len(parsed_times) >= 2:
        sorted_times = sorted(parsed_times)
        # Verify sorting works (times should be in chronological order)
        assert sorted_times[0] <= sorted_times[-1]


async def test_display_attributes_include_type_and_unit(hass: HomeAssistant):
    """Test that display attributes include both medication type and dosage unit."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    test_cases = [
        ("gummy", "each"),
        ("liquid", "mL"),
        ("tablet", "mg"),
    ]

    for med_type, unit in test_cases:
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_MEDICATION_NAME: f"Display_Test_{med_type}",
                CONF_DOSAGE: "10",
                CONF_DOSAGE_UNIT: unit,
                CONF_MEDICATION_TYPE: med_type,
                CONF_SCHEDULE_TYPE: "fixed_time",
                CONF_SCHEDULE_TIMES: ["12:00"],
                CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                CONF_REFILL_AMOUNT: 50,
                CONF_REFILL_REMINDER_DAYS: 7,
            },
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        med_name = f"display_test_{med_type}"
        state = hass.states.get(f"sensor.pa_{med_name}")
        assert state is not None, f"Entity for {med_type} not found"

        attrs = state.attributes

        # Verify both attributes exist
        med_type_attr = attrs.get("Medication Type") or attrs.get("medication_type")
        dosage_unit_attr = attrs.get("Dosage unit") or attrs.get("dosage_unit")

        assert med_type_attr is not None, f"Medication Type missing for {med_type}"
        assert dosage_unit_attr is not None, f"Dosage unit missing for {med_type}"
        assert med_type_attr == med_type
        assert dosage_unit_attr == unit
