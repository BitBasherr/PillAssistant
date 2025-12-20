# Text Overflow and Entity Display Features

This document describes the text overflow handling and entity name display enhancements added to the Pill Assistant integration.

## Features

### 1. Intelligent Entity Name Display

When medications are scheduled relative to sensors (using the "After Sensor Event" schedule type), the system now displays user-friendly entity names instead of raw entity IDs.

#### How It Works

The system uses a three-tier fallback approach:

1. **Friendly Name (First Priority)**: If the entity has a `friendly_name` attribute, that is displayed
2. **Formatted Entity ID (Second Priority)**: If no friendly name exists, the entity ID is formatted by:
   - Removing the domain prefix (e.g., `binary_sensor.`)
   - Splitting on underscores
   - Title-casing each word
3. **Raw Entity ID (Fallback)**: In rare cases where formatting fails, the raw entity ID is shown

#### Examples

| Entity ID | Friendly Name | Display Result |
|-----------|---------------|----------------|
| `binary_sensor.bedroom_motion` | "Bedroom Motion Sensor" | "Bedroom Motion Sensor" |
| `binary_sensor.bedroom_motion_detector` | *(none)* | "Bedroom Motion Detector" |
| `sensor.living_room_temperature_sensor` | *(none)* | "Living Room Temperature Sensor" |
| `binary_sensor.door_sensor_2nd_floor` | *(none)* | "Door Sensor 2nd Floor" |

#### Benefits

- **Improved Readability**: Long entity IDs like `binary_sensor.upstairs_bedroom_motion_detector_battery_low` are now shown as "Upstairs Bedroom Motion Detector Battery Low" or their friendly name
- **User-Friendly Schedules**: Schedule descriptions are much easier to understand
- **Consistent Display**: Works across the entire interface, including medication cards and statistics

### 2. Text Overflow Handling

Medication cards now handle text overflow gracefully to prevent UI layout issues.

#### Default Behavior: Ellipsis

By default, text that exceeds the available space in a detail field (like Schedule, Type, etc.) is truncated with an ellipsis (`...`).

**Example:**
```
Schedule: 2 hrs after Upstairs Bedro...
```

This ensures that:
- Cards maintain consistent sizes
- Long text doesn't break the layout
- The interface remains clean and organized

#### Optional: Uniform Card Sizes

Users can enable the **"Uniform Card Sizes"** option in the header section to:
- Show full text without truncation
- Automatically resize all medication cards to the same height
- Ensure all cards are sized based on the one with the most content

**To Enable:**
1. Check the "Uniform Card Sizes" checkbox in the header (next to "Display Confirmation Banner")
2. All cards will immediately resize to accommodate the longest text in any card
3. The preference is saved to localStorage and persists across sessions

**Benefits of Uniform Sizing:**
- All cards have the same visual weight
- Easier to compare medications at a glance
- Full text is always visible (no truncation)
- Clean, aligned appearance

**When to Use Each Mode:**

- **Default (Ellipsis)**: Best when you have many medications and want a compact view
- **Uniform Sizing**: Best when you have fewer medications and want to see all details in full

## Technical Implementation

### Backend (Python)

**File**: `custom_components/pill_assistant/sensor.py`

Added `_format_entity_name()` method:
```python
def _format_entity_name(self, entity_id: str) -> str:
    """
    Get friendly name for entity or format entity ID nicely.
    
    First tries to get the friendly_name attribute from the entity.
    If that doesn't exist, formats the entity ID by:
    - Removing domain prefix (e.g., 'binary_sensor.')
    - Splitting on underscores
    - Title casing each word
    """
```

This method is used in `_format_schedule_string()` when building the schedule description for relative sensor schedules.

### Frontend (JavaScript/CSS)

**File**: `custom_components/pill_assistant/www/pill-assistant-panel.html`

**CSS Changes:**
```css
.detail-value {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
}

body.uniform-card-sizing .detail-value {
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
}
```

**JavaScript Functions:**
- `toggleUniformCardSizing()`: Handles the checkbox toggle
- `applyUniformCardSizing()`: Measures and applies uniform heights to all card detail fields
- `removeUniformCardSizing()`: Removes uniform sizing and reverts to default
- Updated `loadSettings()` and `saveSettings()` to persist the preference

## Testing

Comprehensive test suite added in `tests/test_entity_name_formatting.py`:

- ✅ Test entity name with friendly name
- ✅ Test entity name without friendly name (formats entity ID)
- ✅ Test entity name with multiple underscores
- ✅ Test entity name with numbers
- ✅ Test entity name fallback when entity not found
- ✅ Test entity name with special characters

All tests pass, validating the three-tier fallback approach works correctly.

## User Experience

### Before
```
Schedule: 2 hrs after binary_sensor.upstairs_bedroom_motion_detector
```
*(Long entity IDs overflow the card or are truncated awkwardly)*

### After (Default)
```
Schedule: 2 hrs after Upstairs Bedro...
```
*(Cleanly truncated with ellipsis)*

### After (with Uniform Sizing enabled)
```
Schedule: 2 hrs after Upstairs Bedroom Motion Detector
```
*(Full text visible, all cards resized uniformly)*

## Configuration

No configuration is required. The entity name formatting works automatically.

The "Uniform Card Sizes" option can be toggled from the header:
- Located next to the "Display Confirmation Banner" checkbox
- Preference is saved automatically
- Can be toggled on/off at any time

## Compatibility

- Works with all Home Assistant entity types (binary_sensor, sensor, switch, etc.)
- Compatible with all schedule types (though primarily beneficial for relative_sensor schedules)
- Responsive and mobile-friendly
- Works in light and dark themes

## Future Enhancements

Possible future improvements:
- Add tooltip on hover to show full text in ellipsis mode
- Allow per-card sizing options
- Add animation when toggling uniform sizing
- Support for custom formatting rules per entity type
