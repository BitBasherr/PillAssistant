"""Test that taking a medication causes its next_dose_time to update and that medications would be resorted accordingly without a reload."""

from datetime import datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_SCHEDULE_TYPE,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
)


async def hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


async def test_reshuffle_after_take(hass: HomeAssistant):
    """Taking the earliest medication should push its next dose later than the others."""
    now = dt_util.now()

    # Create 3 medications with times relative to now (30, 60, 120 minutes)
    t1 = (now + timedelta(minutes=30)).strftime("%H:%M")
    t2 = (now + timedelta(minutes=60)).strftime("%H:%M")
    t3 = (now + timedelta(minutes=120)).strftime("%H:%M")

    entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "reshuffle_a",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: [t1],
            CONF_SCHEDULE_DAYS: [now.strftime("%a").lower()[:3]],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "reshuffle_b",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: [t2],
            CONF_SCHEDULE_DAYS: [now.strftime("%a").lower()[:3]],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry3 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "reshuffle_c",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: [t3],
            CONF_SCHEDULE_DAYS: [now.strftime("%a").lower()[:3]],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    for e in (entry1, entry2, entry3):
        e.add_to_hass(hass)
        await hass.config_entries.async_setup(e.entry_id)
    await hass.async_block_till_done()

    # Grab initial next_dose attributes
    state1 = hass.states.get("sensor.pa_reshuffle_a")
    state2 = hass.states.get("sensor.pa_reshuffle_b")
    state3 = hass.states.get("sensor.pa_reshuffle_c")

    assert state1 is not None and state2 is not None and state3 is not None

    nd1 = state1.attributes.get("Next dose time") or state1.attributes.get(
        "next_dose_time"
    )
    nd2 = state2.attributes.get("Next dose time") or state2.attributes.get(
        "next_dose_time"
    )
    nd3 = state3.attributes.get("Next dose time") or state3.attributes.get(
        "next_dose_time"
    )

    assert nd1 and nd2 and nd3

    # Verify ordering: nd1 < nd2 < nd3
    parsed = [
        (datetime.fromisoformat(x.replace("Z", "+00:00")), idx)
        for idx, x in enumerate((nd1, nd2, nd3))
    ]
    parsed_sorted = sorted(parsed, key=lambda p: p[0])
    assert parsed_sorted[0][1] == 0, "Med A should be earliest"

    # Take medication A
    med_id = hass.states.get("sensor.pa_reshuffle_a").attributes.get("Medication ID")
    await hass.services.async_call(
        DOMAIN, "take_medication", {"medication_id": med_id}, blocking=True
    )
    await hass.async_block_till_done()

    # Reload states
    state1_after = hass.states.get("sensor.pa_reshuffle_a")
    state2_after = hass.states.get("sensor.pa_reshuffle_b")
    state3_after = hass.states.get("sensor.pa_reshuffle_c")

    nd1_after = state1_after.attributes.get(
        "Next dose time"
    ) or state1_after.attributes.get("next_dose_time")

    assert nd1_after is not None

    # After taking, med A's next_dose should be strictly later than at least one other med
    a_time = datetime.fromisoformat(nd1_after.replace("Z", "+00:00"))
    b_time = datetime.fromisoformat(nd2.replace("Z", "+00:00"))

    assert a_time > b_time, "After taking, Med A should be scheduled after Med B"
