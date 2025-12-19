"""Test statistics service response format."""

from datetime import datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    ATTR_END_DATE,
    ATTR_MEDICATION_ID,
    ATTR_START_DATE,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_MEDICATION_NAME,
    CONF_ON_TIME_WINDOW_MINUTES,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TIMES,
    DOMAIN,
    SERVICE_GET_STATISTICS,
    SERVICE_TAKE_MEDICATION,
)


async def test_statistics_service_response_structure(hass: HomeAssistant):
    """Test the structure of the get_statistics service response."""
    # Create medication with on-time window
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Med Stats",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["08:00", "20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ON_TIME_WINDOW_MINUTES: 30,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Take medication a few times
    for _ in range(3):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TAKE_MEDICATION,
            {ATTR_MEDICATION_ID: config_entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Get statistics
    now = dt_util.now()
    start_date = (now - timedelta(days=30)).isoformat()
    end_date = now.isoformat()

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: start_date,
            ATTR_END_DATE: end_date,
        },
        blocking=True,
        return_response=True,
    )

    # Verify response structure
    assert response is not None
    print(f"Response type: {type(response)}")
    print(f"Response keys: {response.keys() if isinstance(response, dict) else 'N/A'}")
    print(f"Response: {response}")

    # The response should contain statistics data
    # Check if it's wrapped or direct
    if "response" in response:
        stats = response["response"]
    else:
        stats = response

    assert "total_entries" in stats
    assert "medications" in stats
    assert "daily_counts" in stats
    assert stats["total_entries"] >= 3  # We took medication 3 times


async def test_statistics_with_no_data(hass: HomeAssistant):
    """Test statistics when no medications have been taken."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Empty Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "pill(s)",
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_ON_TIME_WINDOW_MINUTES: 30,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get statistics without taking any medication
    now = dt_util.now()
    start_date = (now - timedelta(days=30)).isoformat()
    end_date = now.isoformat()

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: start_date,
            ATTR_END_DATE: end_date,
        },
        blocking=True,
        return_response=True,
    )

    # Handle both wrapped and direct response
    if "response" in response:
        stats = response["response"]
    else:
        stats = response

    assert stats is not None
    assert "total_entries" in stats
    assert stats["total_entries"] == 0
    assert "medications" in stats
    assert len(stats["medications"]) == 0
