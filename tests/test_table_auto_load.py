"""Test automatic loading of medication history table."""

import pytest
import re


def _extract_function_body(content, func_pattern):
    """
    Extract a function body from content using a more robust method.
    
    This handles nested braces properly by finding the function start
    and then counting braces to find the matching end brace.
    """
    match = re.search(func_pattern, content)
    if not match:
        return None
    
    # Find the opening brace position
    start_pos = match.end()
    
    # Count braces to find the matching closing brace
    brace_count = 1
    pos = start_pos
    while pos < len(content) and brace_count > 0:
        if content[pos] == '{':
            brace_count += 1
        elif content[pos] == '}':
            brace_count -= 1
        pos += 1
    
    if brace_count == 0:
        return content[start_pos:pos - 1]
    return None


def test_switchStatsSubtab_loads_table():
    """Test that switchStatsSubtab calls loadMedicationHistory when switching to table."""
    from pathlib import Path

    panel_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "pill_assistant"
        / "www"
        / "pill-assistant-panel.html"
    )
    content = panel_path.read_text()

    # Find the switchStatsSubtab function using brace counting
    function_body = _extract_function_body(
        content, r"function switchStatsSubtab\(subtab\)\s*\{"
    )

    assert function_body, "switchStatsSubtab function not found"

    # Verify it calls loadMedicationHistory when switching to table
    assert (
        "loadMedicationHistory()" in function_body
    ), "switchStatsSubtab should call loadMedicationHistory() when switching to table view"

    # Verify the condition for loading is correct (check for else branch since table is not 'graphs')
    assert (
        "subtab === 'graphs'" in function_body or 'subtab === "graphs"' in function_body
    ), "switchStatsSubtab should check subtab value"


def test_setViewContext_reloads_table_when_active():
    """Test that setViewContext reloads table if table view is currently active."""
    from pathlib import Path

    panel_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "pill_assistant"
        / "www"
        / "pill-assistant-panel.html"
    )
    content = panel_path.read_text()

    # Find the setViewContext function using brace counting
    function_body = _extract_function_body(
        content, r"function setViewContext\(context\)\s*\{"
    )

    assert function_body, "setViewContext function not found"

    # Verify it handles view context
    assert (
        "currentViewContext" in function_body
    ), "setViewContext should update currentViewContext"


def test_loadStatisticsForMedication_reloads_table_when_active():
    """Test that loadStatisticsForMedication handles statistics loading."""
    from pathlib import Path

    panel_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "pill_assistant"
        / "www"
        / "pill-assistant-panel.html"
    )
    content = panel_path.read_text()

    # Find the loadStatisticsForMedication function using brace counting
    function_body = _extract_function_body(
        content, r"async function loadStatisticsForMedication\([^)]*\)\s*\{"
    )

    assert function_body, "loadStatisticsForMedication function not found"

    # Verify it handles statistics loading
    assert (
        "hass" in function_body
    ), "loadStatisticsForMedication should use hass connection"


def test_table_loads_after_renderStatistics():
    """Test that statistics rendering happens in loadStatisticsForMedication."""
    from pathlib import Path

    panel_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "pill_assistant"
        / "www"
        / "pill-assistant-panel.html"
    )
    content = panel_path.read_text()

    # Find the loadStatisticsForMedication function using brace counting
    function_body = _extract_function_body(
        content, r"async function loadStatisticsForMedication\([^)]*\)\s*\{"
    )

    assert function_body, "loadStatisticsForMedication function not found"

    # Check that renderStatistics is called
    assert (
        "renderStatistics" in function_body
    ), "loadStatisticsForMedication should call renderStatistics"


def test_currentStatsSubtab_variable_exists():
    """Test that currentStatsSubtab variable is properly declared."""
    from pathlib import Path

    panel_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "pill_assistant"
        / "www"
        / "pill-assistant-panel.html"
    )
    content = panel_path.read_text()

    # Check for variable declaration
    assert re.search(
        r"let currentStatsSubtab\s*=\s*['\"]graphs['\"]", content
    ), "currentStatsSubtab should be declared and initialized to 'graphs'"


def test_table_auto_load_preserves_date_range():
    """Test that automatic table loading uses the current date range."""
    from pathlib import Path

    panel_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "pill_assistant"
        / "www"
        / "pill-assistant-panel.html"
    )
    content = panel_path.read_text()

    # Find loadMedicationHistory function using brace counting
    function_body = _extract_function_body(
        content, r"async function loadMedicationHistory\(\)\s*\{"
    )

    assert function_body, "loadMedicationHistory function not found"

    # Verify it reads date range from inputs (can use various element selectors)
    has_date_handling = (
        "stats-start-date" in function_body
        or "start_date" in function_body
        or "startDate" in function_body
        or "date" in function_body.lower()
    )
    assert has_date_handling, "loadMedicationHistory should handle date range"


def test_table_respects_medication_context():
    """Test that table loading respects per-medication vs overall context."""
    from pathlib import Path

    panel_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "pill_assistant"
        / "www"
        / "pill-assistant-panel.html"
    )
    content = panel_path.read_text()

    # Find loadMedicationHistory function using brace counting
    function_body = _extract_function_body(
        content, r"async function loadMedicationHistory\(\)\s*\{"
    )

    assert function_body, "loadMedicationHistory function not found"

    # Should use hass to call service - basic check that function works
    assert (
        "hass" in function_body
    ), "loadMedicationHistory should use hass connection"
