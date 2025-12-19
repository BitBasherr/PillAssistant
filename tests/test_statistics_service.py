"""Test statistics service response format."""

from datetime import datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant, ServiceResponse
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
    SERVICE_SKIP_MEDICATION,
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
    assert isinstance(response, dict)
    
    # The response should contain statistics data directly
    assert "total_entries" in response
    assert "medications" in response
    assert "daily_counts" in response
    assert response["total_entries"] >= 3  # We took medication 3 times
    
    # Verify medication data
    assert config_entry.entry_id in response["medications"]
    med_stats = response["medications"][config_entry.entry_id]
    assert med_stats["taken_count"] == 3
    assert med_stats["name"] == "Test Med Stats"


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

    # Verify response structure for empty data
    assert response is not None
    assert isinstance(response, dict)
    assert "total_entries" in response
    assert response["total_entries"] == 0
    assert "medications" in response
    assert len(response["medications"]) == 0


async def test_statistics_with_taken_and_skipped(hass: HomeAssistant):
    """Test statistics tracking both taken and skipped medications."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Mixed Actions Med",
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

    # Take medication 5 times
    for _ in range(5):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TAKE_MEDICATION,
            {ATTR_MEDICATION_ID: config_entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Skip medication 2 times
    for _ in range(2):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SKIP_MEDICATION,
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

    # Verify statistics
    assert response is not None
    assert response["total_entries"] == 7  # 5 taken + 2 skipped
    
    med_stats = response["medications"][config_entry.entry_id]
    assert med_stats["taken_count"] == 5
    assert med_stats["skipped_count"] == 2
    assert med_stats["name"] == "Mixed Actions Med"


async def test_statistics_daily_counts(hass: HomeAssistant):
    """Test that statistics properly aggregates daily counts."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Daily Tracking Med",
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

    # Take medication
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

    # Verify daily counts structure
    assert response is not None
    assert "daily_counts" in response
    assert isinstance(response["daily_counts"], dict)
    
    # Should have at least one day with data
    assert len(response["daily_counts"]) > 0
    
    # Check that daily count contains medication data
    for day_key, day_data in response["daily_counts"].items():
        assert isinstance(day_data, dict)
        if config_entry.entry_id in day_data:
            med_day_data = day_data[config_entry.entry_id]
            assert "taken" in med_day_data
            assert "skipped" in med_day_data
            assert "name" in med_day_data

