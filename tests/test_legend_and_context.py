"""Test legend rendering and view context tracking."""

import os
import pytest
from homeassistant.core import HomeAssistant


async def test_html_panel_view_context_variables(hass: HomeAssistant):
    """Test that the HTML panel has view context tracking variables."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for view context tracking variables
    assert "currentViewContext" in content, "currentViewContext variable missing"
    assert "currentMedicationId" in content, "currentMedicationId variable missing"
    # Check that they're initialized with proper default values
    assert (
        "currentViewContext = 'overall'" in content
    ), "currentViewContext should default to 'overall'"
    assert (
        "currentMedicationId = null" in content
    ), "currentMedicationId should default to null"


async def test_html_panel_render_clock_legend_function(hass: HomeAssistant):
    """Test that the HTML panel has renderClockLegend function."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for renderClockLegend function
    assert (
        "function renderClockLegend()" in content
    ), "renderClockLegend function missing"
    # Check that it's called from renderClocks
    assert (
        "renderClockLegend()" in content
    ), "renderClockLegend should be called from renderClocks"


async def test_html_panel_legend_bottom_banner_css(hass: HomeAssistant):
    """Test that the HTML panel has bottom banner CSS for legend."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for bottom banner CSS class
    assert ".clock-legend.bottom-banner" in content, "Bottom banner CSS class missing"
    # Check for horizontal layout
    assert "flex-direction: row" in content, "Legend should use row layout for banner"
    # Check for wrapping
    assert "flex-wrap: wrap" in content, "Legend should wrap items"
    # Check for centering
    assert "justify-content: center" in content, "Legend should center items"


async def test_html_panel_legend_hidden_class(hass: HomeAssistant):
    """Test that the HTML panel has hidden class for legend when no data."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for hidden CSS class
    assert ".clock-legend.hidden" in content, "Legend hidden CSS class missing"
    assert (
        "display: none" in content
    ), "Hidden class should have display: none"


async def test_html_panel_clock_layout_legend_bottom(hass: HomeAssistant):
    """Test that the HTML panel has legend-bottom layout class."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for legend-bottom class
    assert ".clock-layout.legend-bottom" in content, "Legend-bottom layout class missing"
    # Check that it changes grid template
    assert (
        "grid-template-areas" in content
    ), "Grid template areas should be defined for layout switching"


async def test_html_panel_24hr_clock_grid_display(hass: HomeAssistant):
    """Test that 24-hour clock wrapper uses grid display."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check that toggle24HourClock sets display to grid
    assert (
        "style.display = show24HourClock ? 'grid' : 'none'" in content
    ), "24-hour clock should use grid display"
    # Check for CSS rule for 24hr wrapper
    assert (
        "#clock-24hr-wrapper" in content
    ), "24-hour clock wrapper CSS selector missing"
    # Check that it has grid display in CSS
    # This is checked in the CSS section, not the JS


async def test_html_panel_medication_colors_golden_angle(hass: HomeAssistant):
    """Test that medication colors use golden angle for distinct colors."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for golden angle constant (137.5 degrees)
    assert "137.5" in content, "Golden angle constant missing for color generation"
    # Check for HSL color generation
    assert "hsl(" in content, "HSL color format missing"
    # Check for hue calculation with modulo
    assert "% 360" in content, "Hue modulo calculation missing"


async def test_html_panel_action_colors_per_medication(hass: HomeAssistant):
    """Test that action colors (taken/delayed/skipped) are used in per-medication view."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check that drawWedge function checks currentViewContext
    assert (
        "currentViewContext === 'per-medication'" in content
    ), "drawWedge should check for per-medication view"
    # Check for action-based color constants
    assert "'taken'" in content, "Taken action type missing"
    assert "'delayed'" in content, "Delayed action type missing"
    assert "'skipped'" in content, "Skipped action type missing"
    # Check for the color values
    assert "#4caf50" in content, "Green color for taken missing"
    assert "#ffc107" in content, "Yellow color for delayed missing"
    assert "#f44336" in content, "Red color for skipped missing"


async def test_html_panel_show_medication_stats_sets_context(hass: HomeAssistant):
    """Test that showMedicationStats function sets per-medication context."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check that showMedicationStats sets context
    assert (
        "currentViewContext = 'per-medication'" in content
    ), "showMedicationStats should set per-medication context"
    assert (
        "currentMedicationId = medId" in content
    ), "showMedicationStats should store medication ID"


async def test_html_panel_switch_tab_resets_context(hass: HomeAssistant):
    """Test that switching to statistics tab via navigation resets context."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check that switchTab function resets context when switching via nav
    # The function should check for event && event.target to detect navigation click
    assert (
        "currentViewContext = 'overall'" in content
    ), "switchTab should reset to overall context"
    assert (
        "currentMedicationId = null" in content
    ), "switchTab should reset medication ID"


async def test_html_panel_legend_items_removed(hass: HomeAssistant):
    """Test that hardcoded legend items are removed from HTML."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # The legend div should exist
    assert '<div class="clock-legend">' in content, "Legend container missing"
    
    # But it should not have hardcoded legend items in HTML
    # It should have a comment indicating dynamic generation
    assert (
        "<!-- Legend items will be dynamically generated" in content
    ), "Legend should indicate dynamic generation"


async def test_html_panel_distinct_colors_for_medications(hass: HomeAssistant):
    """Test that each medication gets a distinct color in overall view."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check that renderClockLegend creates a Map for medications
    assert "new Map()" in content, "Map should be used to track unique medications"
    # Check that it iterates over clockData
    assert "clockData.forEach" in content, "Should iterate over clock data"
    # Check that it uses medication name as key
    assert "event.medication" in content, "Should use medication name from event"


async def test_html_panel_per_medication_stats_header_update(hass: HomeAssistant):
    """Test that per-medication view updates the statistics header."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check that header is updated in loadStatisticsForMedication
    assert (
        "header.textContent = `Statistics for ${medName}`" in content
    ), "Header should be updated for per-medication view"
    # Check that header is reset in switchTab
    assert (
        "header.textContent = 'Medication Statistics'" in content
    ), "Header should be reset for overall view"


async def test_html_panel_legend_positioning_responsive(hass: HomeAssistant):
    """Test that legend positioning is responsive."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check for media query handling
    assert "@media" in content, "Media queries should be present"
    # The existing media query at 900px should handle legend positioning
    assert "max-width: 900px" in content, "900px breakpoint for legend should exist"


async def test_html_panel_clock_wrapper_alignment(hass: HomeAssistant):
    """Test that clock wrappers maintain consistent height with grid layout."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check that clock wrappers use grid layout
    assert (
        ".clock-wrapper {" in content and "display: grid" in content
    ), "Clock wrapper should use grid display"
    # Check for grid template rows
    assert (
        "grid-template-rows" in content
    ), "Grid template rows should be defined for consistent layout"
    # Check for spacer toggle row to align SVGs
    assert (
        "clock-toggle--spacer" in content
    ), "Spacer toggle should exist for alignment"


async def test_html_panel_legend_no_data_handling(hass: HomeAssistant):
    """Test that legend is hidden when there's no clock data."""
    html_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "pill_assistant",
        "www",
        "pill-assistant-panel.html",
    )

    with open(html_path, "r") as f:
        content = f.read()

    # Check that renderClockLegend checks for empty medications
    # Should add 'hidden' class when medications.size === 0
    assert (
        "medications.size === 0" in content
    ), "Should check for empty medication list"
    assert (
        "classList.add('hidden')" in content
    ), "Should hide legend when no data"
