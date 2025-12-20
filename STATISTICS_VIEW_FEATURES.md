# Statistics View UI Features Guide

This document describes the new UI features added to the Statistics view in Pill Assistant.

## Overview

The Statistics view has been enhanced with several toggleable features that provide better control over how medication data is displayed and analyzed.

## Features

### 1. Graphs|Table Toggle

The statistics view now has two sub-tabs:
- **Graphs (default)**: Displays visual charts and statistics
- **Table**: Shows the medication history editing table

**Usage:**
- The Graphs tab is shown by default when you navigate to Statistics
- Click "Table" to switch to the medication history editing interface
- Selected tab is highlighted in blue with white text (adapts to light mode)

### 2. Per-Medication vs Overall Statistics

When viewing statistics for a specific medication (via the "Statistics" button on a medication card), you can toggle between:
- **[Medication Name]**: Shows statistics only for that specific medication
- **Overall**: Shows statistics for all medications

**Usage:**
- Click a medication's "Statistics" button to enter per-medication mode
- The toggle shows the medication name on the left button
- Click "Overall" to switch back to viewing all medications
- The view context is retained when switching between Graphs and Table tabs

### 3. Yesterday Toggle

A convenient checkbox for quickly viewing yesterday's data in statistics.

**Usage:**
- Check "Yesterday" to set the date range to yesterday
- The checkbox automatically un-checks if you manually change the date range
- Works alongside the existing "Today" checkbox

### 4. Bar Chart Time/Quantity Mode

When viewing the Bar chart, you can toggle between two modes:
- **Time (default)**: Shows medications grouped by 4-hour time chunks (0:00-4:00, 4:00-8:00, etc.)
- **Quantity**: Shows the traditional quantity view by date

**Time Chunks:**
- 0:00-4:00
- 4:00-8:00
- 8:00-12:00
- 12:00-16:00
- 16:00-20:00
- 20:00-24:00

**Usage:**
- The Time|Quantity toggle only appears when Bar chart is selected
- Click "Time" to view medications by time of day
- Click "Quantity" to view medications by count per date
- Your selection is saved across sessions

### 5. Auto-Fallback for Empty Data

The Clock-Pie view now automatically falls back to the last date with data if the selected date has no medication events.

**Behavior:**
- If you select today but no medications have been taken today
- The view automatically switches to the most recent date with data
- The date picker updates to show the fallback date
- Prevents showing empty visualizations

## Visual Design

All toggle buttons follow a consistent design:
- **Active state**: Blue background (#2196F3) with white text
- **Inactive state**: Light background with dark text
- **Light mode**: Automatically adjusts colors for readability
- **Hover effect**: Slight background change on hover

## Dosage Display Improvements

Dosage displays have been improved for clarity:

### Before:
- "1.0 Tablet(s) (tablet(s))"
- "2.0 Tablet(s) (tablet(s))"
- "500 Tablet(s) (mg)"

### After:
- "1 Tablet" or "1.0 Tablet"
- "2 Tablets"
- "500 mg"

### Pluralization Rules:
- Singular (1.0): "1 Tablet", "1 Capsule", "1 Gummy"
- Plural (!= 1.0): "2 Tablets", "3 Capsules", "2 Gummies"
- Specific units: Always show unit instead of type (e.g., "500 mg" not "500 tablets")
- Supported specific units: mg, mL, g, mcg, tsp, TBSP, units, IU

## Technical Details

### State Persistence

The following preferences are saved in localStorage:
- `pillAssistantStatsSubtab`: Current sub-tab (graphs or table)
- `pillAssistantChartType`: Selected chart type (clock, bar, or plot)
- `pillAssistantBarMode`: Bar chart mode (time or quantity)

### View Context

The view context (per-medication vs overall) is maintained in memory during the session:
- `currentViewContext`: "per-medication" or "overall"
- `currentMedicationId`: ID of the selected medication (when in per-medication mode)

## Keyboard and Accessibility

All toggle buttons are keyboard accessible:
- Tab to navigate between buttons
- Enter/Space to activate
- Screen readers will announce button states

## Browser Compatibility

These features work in all modern browsers:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

localStorage is required for state persistence across sessions.

## Examples

### Viewing a Specific Medication's Statistics

1. Click the "📊 Statistics" button on a medication card
2. You're taken to the Statistics tab in per-medication mode
3. The toggle shows: `[Medication Name] | Overall`
4. The header shows: "Statistics for [Medication Name]"
5. Click "Overall" to see all medications

### Using Time-Based Bar Chart

1. Navigate to Statistics tab
2. Select "Bar" chart type
3. The "Time | Quantity" toggle appears
4. Click "Time" to see medications by time of day
5. View medications grouped in 4-hour chunks

### Viewing Yesterday's Data

1. Navigate to Statistics tab
2. Check the "Yesterday" checkbox
3. Date range automatically sets to yesterday
4. Charts and tables update to show yesterday's data
5. Checkbox auto-unchecks if you manually change dates

## Troubleshooting

**Q: Toggle buttons don't show up**
A: Make sure you're on the Statistics tab and that JavaScript is enabled

**Q: My selection isn't saved across sessions**
A: Check that your browser allows localStorage for the site

**Q: Auto-fallback doesn't work**
A: Auto-fallback only applies to Clock-Pie view when there's no data for the selected date

**Q: Bar chart time mode shows empty**
A: The time mode uses dose_events data - ensure you have taken medications with timestamps

## Future Enhancements

Planned improvements:
- Export statistics data
- Custom time chunk sizes for bar chart
- Additional chart types
- Medication comparison view
