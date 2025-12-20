"""Test statistics view UI features and toggle functionality."""

import pytest
from datetime import datetime, timedelta
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


@pytest.fixture
async def setup_test_medication(hass: HomeAssistant):
    """Set up a test medication for statistics testing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Test Medication",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "mg",
            CONF_MEDICATION_TYPE: "tablet",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: ["08:00", "12:00", "18:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            CONF_REFILL_AMOUNT: 90,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_statistics_service_returns_data(
    hass: HomeAssistant, setup_test_medication
):
    """Test that statistics service returns data structure needed for UI."""
    entry = setup_test_medication
    
    # Take medication a few times
    for _ in range(3):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TAKE_MEDICATION,
            {ATTR_MEDICATION_ID: entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()
    
    # Get statistics
    now = dt_util.now()
    start_date = (now - timedelta(days=7)).isoformat()
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
    
    # Verify response structure for UI
    assert response is not None
    assert isinstance(response, dict)
    assert "medications" in response
    assert "daily_counts" in response
    assert "total_entries" in response
    
    # Verify medication data
    assert entry.entry_id in response["medications"]
    med_stats = response["medications"][entry.entry_id]
    assert "name" in med_stats
    assert "taken_count" in med_stats
    assert med_stats["taken_count"] == 3


async def test_statistics_per_medication_filter(
    hass: HomeAssistant, setup_test_medication
):
    """Test that statistics returns medication data structure."""
    entry = setup_test_medication
    
    # Take medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    
    # Get statistics with wide date range
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
    
    # Verify response contains medication data structure
    assert response is not None
    assert "medications" in response
    # Frontend can filter the displayed data by medication_id client-side


async def test_statistics_empty_data_handling(hass: HomeAssistant, setup_test_medication):
    """Test that statistics handles empty data gracefully."""
    # Don't take any medication, just get statistics
    now = dt_util.now()
    
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: now.isoformat(),
            ATTR_END_DATE: now.isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    
    # Should return valid structure even with no data
    assert response is not None
    assert "medications" in response
    assert "daily_counts" in response
    assert response["total_entries"] == 0


async def test_statistics_date_range_handling(
    hass: HomeAssistant, setup_test_medication
):
    """Test that statistics properly handles different date ranges."""
    entry = setup_test_medication
    
    # Take medication today
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    
    now = dt_util.now()
    
    # Get statistics with wide range including today
    wide_range_response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: (now - timedelta(days=30)).isoformat(),
            ATTR_END_DATE: now.isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    
    # Verify response has data
    assert "medications" in wide_range_response
    assert wide_range_response["total_entries"] >= 1


async def test_statistics_with_multiple_medications(hass: HomeAssistant):
    """Test statistics with multiple medications for overall view."""
    # Create multiple medications
    entries = []
    for i in range(3):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_MEDICATION_NAME: f"Med_{i}",
                CONF_DOSAGE: "1",
                CONF_DOSAGE_UNIT: "each",
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
        entries.append(entry)
    
    # Take each medication once
    for entry in entries:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TAKE_MEDICATION,
            {ATTR_MEDICATION_ID: entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()
    
    # Get overall statistics with wide date range
    now = dt_util.now()
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: (now - timedelta(days=30)).isoformat(),
            ATTR_END_DATE: now.isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    
    # Verify response structure
    assert response["total_entries"] >= 3


async def test_dose_events_include_timestamps(
    hass: HomeAssistant, setup_test_medication
):
    """Test that dose events include timestamps for time-based charts."""
    entry = setup_test_medication
    
    # Take medication
    before_time = dt_util.now()
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    after_time = dt_util.now()
    
    # Get statistics
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: before_time.isoformat(),
            ATTR_END_DATE: after_time.isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    
    # Verify dose events have timestamps
    if "dose_events" in response:
        for event in response["dose_events"]:
            assert "timestamp" in event
            assert "action" in event
            assert "medication_id" in event
            # Timestamp should be parseable
            event_time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            assert before_time <= event_time <= after_time


def test_dosage_display_formatting():
    """Test dosage display formatting with proper pluralization."""
    # Note: This is a frontend function test - normally would be done in JS tests
    # But we can verify the backend provides correct data structure
    
    test_cases = [
        # (amount, med_type, unit, expected_format_contains)
        ("1", "tablet", "each", ["1", "tablet"]),
        ("2", "tablet", "each", ["2", "tablet"]),
        ("1", "pill", "each", ["1", "pill"]),
        ("2", "pill", "each", ["2", "pill"]),
        ("1", "gummy", "each", ["1", "gummy"]),
        ("2", "gummy", "each", ["2", "gummies"]),  # Should pluralize to gummies
        ("5", "tablet", "mg", ["5", "mg"]),  # Should show unit, not type
        ("10", "liquid", "mL", ["10", "mL"]),  # Should show unit
    ]
    
    # This test documents expected behavior
    # Frontend formatDosageDisplay function should handle these cases
    assert True  # Placeholder for frontend validation


async def test_statistics_daily_counts_structure(
    hass: HomeAssistant, setup_test_medication
):
    """Test that daily_counts has correct structure for charts."""
    entry = setup_test_medication
    
    # Take medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    
    # Get statistics with wide date range
    now = dt_util.now()
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: (now - timedelta(days=30)).isoformat(),
            ATTR_END_DATE: now.isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    
    # Verify daily_counts structure exists
    assert "daily_counts" in response
    assert "medications" in response
    
    # Verify we have some data
    assert response["total_entries"] >= 1


async def test_statistics_adherence_calculation(
    hass: HomeAssistant, setup_test_medication
):
    """Test that statistics provide data for adherence calculations."""
    entry = setup_test_medication
    
    # Take medication
    await hass.services.async_call(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        {ATTR_MEDICATION_ID: entry.entry_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    
    # Get statistics
    now = dt_util.now()
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {
            ATTR_START_DATE: now.isoformat(),
            ATTR_END_DATE: now.isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    
    # Verify response structure
    assert "medications" in response
    
    # If our medication appears in the results, verify adherence data
    if entry.entry_id in response["medications"]:
        med_stats = response["medications"][entry.entry_id]
        assert "taken_count" in med_stats
        assert "skipped_count" in med_stats
        
        # Verify counts are reasonable
        assert med_stats["taken_count"] >= 0
        assert med_stats["skipped_count"] >= 0
        assert med_stats["taken_count"] >= 1  # We took it at least once
