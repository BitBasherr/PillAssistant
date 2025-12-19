"""Test dosage unit normalization."""

import pytest
from custom_components.pill_assistant.sensor import normalize_dosage_unit
from custom_components.pill_assistant.const import (
    DEFAULT_DOSAGE_UNIT,
    SPECIFIC_DOSAGE_UNITS,
)


def test_normalize_dosage_unit_specific_units():
    """Test that specific units are preserved."""
    for unit in SPECIFIC_DOSAGE_UNITS:
        assert normalize_dosage_unit(unit) == unit


def test_normalize_dosage_unit_embedded_specific_units():
    """Test that specific units embedded in strings are extracted."""
    assert normalize_dosage_unit("500mg") == "mg"
    assert normalize_dosage_unit("10mL") == "mL"
    assert normalize_dosage_unit("2g") == "g"
    assert normalize_dosage_unit("1tsp") == "tsp"
    assert normalize_dosage_unit("2TBSP") == "TBSP"


def test_normalize_dosage_unit_generic_types():
    """Test that generic types are preserved."""
    assert normalize_dosage_unit("pill(s)") == "pill(s)"
    assert normalize_dosage_unit("tablet(s)") == "tablet(s)"
    assert normalize_dosage_unit("capsule(s)") == "capsule(s)"
    assert normalize_dosage_unit("gummy/gummies") == "gummy/gummies"


def test_normalize_dosage_unit_none_or_empty():
    """Test that None or empty string defaults to DEFAULT_DOSAGE_UNIT."""
    assert normalize_dosage_unit(None) == DEFAULT_DOSAGE_UNIT
    assert normalize_dosage_unit("") == DEFAULT_DOSAGE_UNIT


def test_normalize_dosage_unit_case_insensitive():
    """Test that unit matching is case insensitive for embedded units."""
    assert normalize_dosage_unit("500MG") == "mg"
    assert normalize_dosage_unit("10ML") == "mL"
    assert normalize_dosage_unit("2G") == "g"
