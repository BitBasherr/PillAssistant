"""Test flexible time input functionality."""

import pytest
from custom_components.pill_assistant.config_flow import normalize_time_input


def test_normalize_time_with_colon():
    """Test normalizing time input with colon format."""
    # Standard 24-hour format with colon
    time, needs_clarification = normalize_time_input("08:00")
    assert time == "08:00"
    assert not needs_clarification
    
    time, needs_clarification = normalize_time_input("20:30")
    assert time == "20:30"
    assert not needs_clarification


def test_normalize_time_without_colon():
    """Test normalizing time input without colon."""
    # 4-digit format without colon - ambiguous
    time, needs_clarification = normalize_time_input("1015")
    assert time == "10:15"
    assert needs_clarification
    
    # 3-digit format without colon - ambiguous
    time, needs_clarification = normalize_time_input("915")
    assert time == "09:15"
    assert needs_clarification
    
    # 24-hour format without colon - unambiguous
    time, needs_clarification = normalize_time_input("2030")
    assert time == "20:30"
    assert not needs_clarification


def test_normalize_time_with_am_pm():
    """Test normalizing time input with AM/PM."""
    # With AM
    time, needs_clarification = normalize_time_input("10:15AM")
    assert time == "10:15"
    assert not needs_clarification
    
    # With PM
    time, needs_clarification = normalize_time_input("10:15PM")
    assert time == "22:15"
    assert not needs_clarification
    
    # Without colon but with AM
    time, needs_clarification = normalize_time_input("1015AM")
    assert time == "10:15"
    assert not needs_clarification
    
    # Without colon but with PM
    time, needs_clarification = normalize_time_input("1015PM")
    assert time == "22:15"
    assert not needs_clarification
    
    # Edge case: 12 AM (midnight)
    time, needs_clarification = normalize_time_input("12:00AM")
    assert time == "00:00"
    assert not needs_clarification
    
    # Edge case: 12 PM (noon)
    time, needs_clarification = normalize_time_input("12:00PM")
    assert time == "12:00"
    assert not needs_clarification


def test_normalize_time_with_spaces():
    """Test normalizing time input with spaces."""
    # Time with colon is treated as 24-hour format (unambiguous)
    time, needs_clarification = normalize_time_input("  10:15  ")
    assert time == "10:15"
    assert not needs_clarification
    
    time, needs_clarification = normalize_time_input("  10:15 AM  ")
    assert time == "10:15"
    assert not needs_clarification


def test_normalize_time_lowercase_ampm():
    """Test normalizing time input with lowercase am/pm."""
    time, needs_clarification = normalize_time_input("10:15am")
    assert time == "10:15"
    assert not needs_clarification
    
    time, needs_clarification = normalize_time_input("10:15pm")
    assert time == "22:15"
    assert not needs_clarification


def test_normalize_time_invalid():
    """Test normalizing invalid time input."""
    # Invalid minutes
    time, needs_clarification = normalize_time_input("10:99")
    assert time is None
    assert not needs_clarification
    
    # Invalid hours with AM/PM
    time, needs_clarification = normalize_time_input("13:00AM")
    assert time is None
    assert not needs_clarification
    
    # Non-numeric
    time, needs_clarification = normalize_time_input("abc")
    assert time is None
    assert not needs_clarification
    
    # Too long
    time, needs_clarification = normalize_time_input("12345")
    assert time is None
    assert not needs_clarification


def test_normalize_time_edge_cases():
    """Test edge cases for time normalization."""
    # Midnight in 24-hour format
    time, needs_clarification = normalize_time_input("00:00")
    assert time == "00:00"
    assert not needs_clarification
    
    # Single digit hour
    time, needs_clarification = normalize_time_input("9")
    assert time == "09:00"
    assert needs_clarification
    
    # Two digit hour
    time, needs_clarification = normalize_time_input("10")
    assert time == "10:00"
    assert needs_clarification
    
    # Hour 13+ is unambiguous
    time, needs_clarification = normalize_time_input("13:00")
    assert time == "13:00"
    assert not needs_clarification
