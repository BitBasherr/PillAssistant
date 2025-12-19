"""Fixtures for testing Pill Assistant."""

import os
import shutil
import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for testing."""
    yield


@pytest.fixture(autouse=True)
def cleanup_log_files(hass):
    """Clean up CSV log files from Pill Assistant to ensure test isolation."""
    logs_dir = hass.config.path("Pill Assistant", "Logs")
    if os.path.exists(logs_dir):
        shutil.rmtree(logs_dir, ignore_errors=True)
    yield
    if os.path.exists(logs_dir):
        shutil.rmtree(logs_dir, ignore_errors=True)


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry for testing."""
    return MockConfigEntry(
        domain="pill_assistant",
        data={
            "medication_name": "Test Medication",
            "dosage": "100",
            "dosage_unit": "mg",
            "schedule_type": "fixed_time",
            "schedule_times": ["08:00", "20:00"],
            "schedule_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "refill_amount": 30,
            "refill_reminder_days": 7,
            "notes": "Test notes",
        },
    )
