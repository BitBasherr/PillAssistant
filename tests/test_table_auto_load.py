"""Test automatic loading of medication history table."""

import pytest
import re


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

    # Find the switchStatsSubtab function
    match = re.search(
        r"function switchStatsSubtab\(subtab\)\s*\{(.*?)^\s*\}",
        content,
        re.MULTILINE | re.DOTALL,
    )

    assert match, "switchStatsSubtab function not found"
    function_body = match.group(1)

    # Verify it calls loadMedicationHistory when switching to table
    assert (
        "loadMedicationHistory()" in function_body
    ), "switchStatsSubtab should call loadMedicationHistory() when switching to table view"

    # Verify the condition for loading is correct
    assert (
        "subtab === 'table'" in function_body or 'subtab === "table"' in function_body
    ), "switchStatsSubtab should check if subtab is 'table'"


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

    # Find the setViewContext function
    match = re.search(
        r"function setViewContext\(context\)\s*\{(.*?)^\s*\}",
        content,
        re.MULTILINE | re.DOTALL,
    )

    assert match, "setViewContext function not found"
    function_body = match.group(1)

    # Verify it calls loadMedicationHistory when table is active
    assert (
        "loadMedicationHistory()" in function_body
    ), "setViewContext should call loadMedicationHistory() when table view is active"

    # Verify it checks currentStatsSubtab
    assert (
        "currentStatsSubtab === 'table'" in function_body
        or 'currentStatsSubtab === "table"' in function_body
    ), "setViewContext should check if currentStatsSubtab is 'table'"


def test_loadStatisticsForMedication_reloads_table_when_active():
    """Test that loadStatisticsForMedication reloads table if table view is currently active."""
    from pathlib import Path

    panel_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "pill_assistant"
        / "www"
        / "pill-assistant-panel.html"
    )
    content = panel_path.read_text()

    # Find the loadStatisticsForMedication function
    match = re.search(
        r"async function loadStatisticsForMedication\([^)]*\)\s*\{(.*?)^\s*\}",
        content,
        re.MULTILINE | re.DOTALL,
    )

    assert match, "loadStatisticsForMedication function not found"
    function_body = match.group(1)

    # Verify it calls loadMedicationHistory when table is active
    assert (
        "loadMedicationHistory()" in function_body
    ), "loadStatisticsForMedication should call loadMedicationHistory() when table view is active"

    # Verify it checks currentStatsSubtab
    assert (
        "currentStatsSubtab === 'table'" in function_body
        or 'currentStatsSubtab === "table"' in function_body
    ), "loadStatisticsForMedication should check if currentStatsSubtab is 'table'"


def test_table_loads_after_renderStatistics():
    """Test that table loading happens after renderStatistics in loadStatisticsForMedication."""
    from pathlib import Path

    panel_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "pill_assistant"
        / "www"
        / "pill-assistant-panel.html"
    )
    content = panel_path.read_text()

    # Find the loadStatisticsForMedication function
    match = re.search(
        r"async function loadStatisticsForMedication\([^)]*\)\s*\{(.*?)^\s*\}",
        content,
        re.MULTILINE | re.DOTALL,
    )

    assert match, "loadStatisticsForMedication function not found"
    function_body = match.group(1)

    # Check that loadMedicationHistory comes after renderStatistics
    render_pos = function_body.find("renderStatistics")
    load_history_pos = function_body.find("loadMedicationHistory()")

    assert render_pos > 0, "renderStatistics call not found"
    assert load_history_pos > 0, "loadMedicationHistory call not found"
    assert (
        load_history_pos > render_pos
    ), "loadMedicationHistory should be called after renderStatistics"


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

    # Find loadMedicationHistory function
    match = re.search(
        r"async function loadMedicationHistory\(\)\s*\{(.*?)^\s*\}",
        content,
        re.MULTILINE | re.DOTALL,
    )

    assert match, "loadMedicationHistory function not found"
    function_body = match.group(1)

    # Verify it reads date range from inputs
    assert (
        "getElementById('stats-start-date')" in function_body
        or 'getElementById("stats-start-date")' in function_body
    ), "loadMedicationHistory should read start date from date picker"
    assert (
        "getElementById('stats-end-date')" in function_body
        or 'getElementById("stats-end-date")' in function_body
    ), "loadMedicationHistory should read end date from date picker"


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

    # Find loadMedicationHistory function
    match = re.search(
        r"async function loadMedicationHistory\(\)\s*\{(.*?)^\s*\}",
        content,
        re.MULTILINE | re.DOTALL,
    )

    assert match, "loadMedicationHistory function not found"
    function_body = match.group(1)

    # Should check for currentViewContext and currentMedicationId
    # The function should conditionally add medication_id to service data
    assert (
        "currentViewContext" in function_body or "currentMedicationId" in function_body
    ), "loadMedicationHistory should check view context or medication ID"
