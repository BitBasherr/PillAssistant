"""Test medication-specific statistics filtering."""

import pytest
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
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
    SERVICE_GET_STATISTICS,
    SERVICE_TAKE_MEDICATION,
    ATTR_START_DATE,
    ATTR_END_DATE,
    ATTR_MEDICATION_ID,
)


async def test_statistics_per_medication_filter(hass: HomeAssistant):
    """Test that statistics correctly filters by medication_id."""
    # Create two medications
    entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med1",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "mg",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 90,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry1.add_to_hass(hass)
    await hass.config_entries.async_setup(entry1.entry_id)

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Med2",
            CONF_DOSAGE: "2",
            CONF_DOSAGE_UNIT: "mg",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["12:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 90,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    # Take Med1 twice and Med2 once
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry1.entry_id},
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry1.entry_id},
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry2.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    now = dt_util.now()
    start_date = (now - timedelta(days=7)).isoformat()
    end_date = now.isoformat()

    # Get statistics for all medications
    all_stats = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: start_date,
            ATTR_END_DATE: end_date,
        },
        blocking=True,
        return_response=True,
    )

    # Verify both medications are in the response
    assert all_stats is not None
    assert "medications" in all_stats
    assert entry1.entry_id in all_stats["medications"]
    assert entry2.entry_id in all_stats["medications"]
    assert all_stats["medications"][entry1.entry_id]["taken_count"] == 2
    assert all_stats["medications"][entry2.entry_id]["taken_count"] == 1
    assert all_stats["total_entries"] == 3

    # Get statistics for Med1 only
    med1_stats = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: start_date,
            ATTR_END_DATE: end_date,
            ATTR_MEDICATION_ID: entry1.entry_id,
        },
        blocking=True,
        return_response=True,
    )

    # Verify only Med1 is in the response
    assert med1_stats is not None
    assert "medications" in med1_stats
    assert entry1.entry_id in med1_stats["medications"]
    assert entry2.entry_id not in med1_stats["medications"]
    assert med1_stats["medications"][entry1.entry_id]["taken_count"] == 2
    assert med1_stats["total_entries"] == 2

    # Get statistics for Med2 only
    med2_stats = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: start_date,
            ATTR_END_DATE: end_date,
            ATTR_MEDICATION_ID: entry2.entry_id,
        },
        blocking=True,
        return_response=True,
    )

    # Verify only Med2 is in the response
    assert med2_stats is not None
    assert "medications" in med2_stats
    assert entry1.entry_id not in med2_stats["medications"]
    assert entry2.entry_id in med2_stats["medications"]
    assert med2_stats["medications"][entry2.entry_id]["taken_count"] == 1
    assert med2_stats["total_entries"] == 1
