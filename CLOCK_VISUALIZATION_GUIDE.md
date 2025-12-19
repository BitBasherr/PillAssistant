# Clock Visualization Feature Guide

## Overview
The Clock Visualization feature provides an intuitive, visual way to track your medication adherence throughout the day. Instead of just seeing numbers and lists, you can now see your doses displayed on clock faces, making it easy to spot patterns and gaps in your medication schedule.

## Accessing Clock Visualizations

1. Open the Pill Assistant panel from your Home Assistant sidebar
2. Click on the **📊 Statistics** tab
3. Scroll down to the **Daily Medication Timeline** section

## Understanding the Clocks

### 12-Hour Clock
- Displays medications taken during a 12-hour period
- Use the **AM** and **PM** buttons to toggle between morning and evening
- Perfect for focusing on specific parts of your day
- Hour markers at 12, 3, 6, and 9 positions

### 24-Hour Clock
- Shows all doses taken throughout the entire day
- No toggle needed - sees the complete picture at once
- Hour markers at 0, 6, 12, and 18 positions
- Useful for spotting overall daily patterns

## Reading the Wedge Indicators

Each medication dose appears as a colored wedge on the clock:

### Color Coding
- **🟢 Green Wedges**: Doses taken successfully
  - Indicates you took your medication as scheduled
  - The ideal state for all your doses

- **🟡 Yellow Wedges**: Doses delayed or snoozed
  - Shows when you delayed taking a medication
  - Indicates you acknowledged the reminder but postponed
  - Still better than skipping entirely

- **🔴 Red Wedges**: Doses skipped
  - Indicates a dose was marked as skipped
  - Helps identify when you intentionally missed a dose
  - Important for tracking adherence patterns

### Wedge Position
- **Angle**: The position around the clock shows the time the dose was taken/skipped
  - Example: 3 o'clock position = 3 PM (or 15:00)
  - Example: 6 o'clock position = 6 AM/PM (or 6:00/18:00)

- **Length**: Wedges extend from the clock center outward beyond the circle
  - Makes them easy to see and distinguish
  - Creates a visual "burst" at each dose time

### Interactive Features
- **Hover for Details**: Hover over any wedge to see:
  - Medication name
  - Status (taken/delayed/skipped)
  - Approximate time

## Using the Date Picker

### Selecting a Date
1. Click on the date input field at the top of the visualization
2. Choose any date from the calendar
3. The clocks will automatically update to show that day's data

### Date Range
- **Default**: Today's date in your local timezone
- **Available Range**: Any date for which medication data exists
- **Maximum**: Today (you can't view future dates)

### Use Cases
- **Daily Review**: Check how you did today
- **Weekly Pattern**: Review the same day each week to spot patterns
- **Troubleshooting**: Go back to a specific date when you had issues
- **Progress Tracking**: Compare adherence over time

## Interpreting the Visualization

### Perfect Adherence
If you see only green wedges at all scheduled times, congratulations! You're taking your medications as prescribed.

### Identifying Issues
- **Many red wedges**: Consider if you need to adjust your schedule or set up better reminders
- **Yellow wedges clustered at certain times**: That time might not work well for you
- **Empty periods**: Times when no medications are scheduled

### Pattern Recognition
Over time, you may notice:
- Times of day when you're more likely to miss doses
- Days of the week with better/worse adherence
- Improvements after schedule adjustments

## Tips for Best Results

### 1. Regular Review
- Check the visualization daily to stay aware of your adherence
- Use the date picker to review the past week every Sunday

### 2. Use with Statistics
- Combine clock view with the numerical statistics above it
- Get both visual and quantitative feedback on your adherence

### 3. Adjust Schedules
- If you see patterns of missed doses at certain times, edit your medication schedule
- The clock makes it obvious which times work best for you

### 4. Share with Healthcare Providers
- Take screenshots of the clock visualization
- Shows your medication patterns more clearly than just numbers
- Helps doctors understand your real-world adherence challenges

## Technical Details

### Data Source
- Clock visualizations pull from the same statistics service as the charts
- Data includes all medication events (taken, skipped, snoozed) with timestamps
- Filtered by the selected date

### Update Frequency
- Clocks update automatically when you:
  - Change the selected date
  - Switch between AM/PM on the 12-hour clock
  - Refresh the statistics data
  - Take/skip a medication (after page reload)

### Theme Support
- Clocks automatically adapt to your Home Assistant theme
- **Light Mode**: White clock face, dark text and lines
- **Dark Mode**: Dark clock face, light text and lines

### Responsive Design
- Clocks stack vertically on mobile devices
- Touch-friendly for selecting dates and toggling AM/PM
- Maintains readability on all screen sizes

## Troubleshooting

### No Wedges Showing
- **Cause**: No medication events recorded for the selected date
- **Solution**: Select a different date or take/skip a medication to generate data

### Wedges Overlapping
- **Cause**: Multiple medications taken at the same time
- **Solution**: Hover over overlapping wedges to see each one's details

### Clock Not Updating
- **Cause**: Data hasn't refreshed after a recent dose
- **Solution**: Click the "Update" button in the Statistics section header

### Date Picker Not Working
- **Cause**: Browser compatibility issue
- **Solution**: Type the date directly in YYYY-MM-DD format (e.g., 2025-12-19)

## Examples

### Example 1: Morning Person
```
12-Hour Clock (AM selected):
- Green wedges at 6:00, 8:00, 10:00
- Interpretation: Successfully took all morning medications
```

### Example 2: Evening Struggles
```
12-Hour Clock (PM selected):
- Green wedge at 6:00
- Yellow wedge at 8:00 (delayed from scheduled time)
- Red wedge at 10:00 (skipped)
- Interpretation: Evening routine needs improvement
```

### Example 3: Full Day View
```
24-Hour Clock:
- Green wedges spread around clock at 8:00, 14:00, 20:00
- Interpretation: Good adherence with 3x daily medication
```

## Future Enhancements

Potential future additions to the clock visualization:
- Week view with 7 clocks side by side
- Comparison mode showing two dates
- Scheduled vs. actual wedge comparison
- Animation showing dose progression throughout the day
- Export clock image for sharing

## Related Features

- **Statistics Tab**: Overall adherence numbers and trends
- **Medication Cards**: Individual medication tracking
- **Date Range Picker**: Compare different time periods
- **Adherence Charts**: Bar charts showing per-medication adherence

## Feedback and Support

If you have suggestions for improving the clock visualization:
1. Open an issue on the GitHub repository
2. Include screenshots if reporting visual bugs
3. Describe your use case for requested features

---

**Note**: This feature requires Home Assistant 2024.6.0 or later and Pill Assistant integration version 2.0.0+.
