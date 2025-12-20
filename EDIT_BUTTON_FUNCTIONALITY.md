# Edit Button Functionality

This document describes the edit button implementation and navigation flow for medications in the Pill Assistant integration.

## Overview

Each medication card in the Pill Assistant interface includes an "✏️ Edit" button that allows users to modify medication settings. The button opens the Home Assistant configuration flow for that specific medication.

## How It Works

When a user clicks the Edit button:

1. **Entry ID Resolution**: The button receives the medication's config entry ID (stored as `medication_id` in the sensor attributes)
2. **Navigation**: The system navigates to `/config/integrations/config_entry/{entry_id}` which opens the medication's options flow
3. **Options Flow**: Home Assistant's standard configuration UI opens, showing all editable fields for that medication

## Editable Fields

Through the edit/options flow, users can modify:

### Basic Information
- Medication name
- Dosage amount
- Dosage unit
- Medication type (pill, tablet, capsule, etc.)
- Current quantity

### Schedule Settings
Users can change between schedule types:
- **Fixed Time**: Specific times on specific days
- **After Another Medication**: Relative to another medication's dose
- **After Sensor Event**: Triggered by an entity state change

Each schedule type has its own configuration options:
- Schedule times
- Schedule days
- Offset hours/minutes
- Sensor trigger values
- Duplicate trigger prevention

### Refill & Notification Settings
- Refill amount
- Refill reminder threshold
- Notification services
- Snooze duration
- Automatic notifications toggle
- On-time window

## Navigation Implementation

The edit button uses multiple fallback navigation methods for maximum compatibility:

### Method 1: Direct HASS Navigation (Preferred)
```javascript
if (typeof hass.navigate === 'function') {
    hass.navigate(path);
}
```
This is the cleanest method and works when the panel has access to the Home Assistant connection object.

### Method 2: Parent Window Navigation
```javascript
const haElement = window.parent.document.querySelector('home-assistant');
if (haElement && haElement.hass) {
    haElement.hass.navigate(path);
}
```
Used when the panel is embedded in an iframe or side panel.

### Method 3: History API Fallback
```javascript
window.parent.history.pushState(null, '', path);
window.parent.dispatchEvent(new CustomEvent('location-changed', {
    detail: { replace: false }
}));
```
Direct history manipulation as a last resort.

### Error Handling
If all navigation methods fail, the user receives a helpful error message directing them to use the manual path:
```
Error: Cannot navigate. Please edit medication through 
Settings → Devices & Services → Configure
```

## Testing

Comprehensive tests verify the edit functionality:

### Test Coverage (`tests/test_edit_medication_navigation.py`)

✅ **test_edit_medication_entry_id_availability**
- Verifies config entries have valid entry IDs

✅ **test_medication_sensor_exposes_entry_id**
- Confirms sensors expose the entry ID in attributes as "Medication ID"

✅ **test_options_flow_accessible_with_entry_id**
- Validates that the options flow can be accessed using the entry ID

✅ **test_multiple_medications_have_unique_entry_ids**
- Ensures each medication has a unique entry ID for proper navigation

✅ **test_edit_medication_preserves_existing_data**
- Confirms that editing preserves unchanged fields

All tests pass (5/5) ✅

## User Flow Example

1. User clicks "✏️ Edit" on a medication card
2. System navigates to the configuration page
3. User sees a form with current medication settings
4. User modifies any fields they want to change
5. User clicks "Submit"
6. Changes are saved and the medication card updates

## Button Location

The Edit button is located in the card management section at the bottom of each medication card:

```
[📊 Statistics] [✏️ Edit] [🗑️ Delete]
```

## CSS Styling

```css
.btn-edit {
    background: #2196f3;
    color: white;
}
.btn-edit:hover {
    background: #1976d2;
}
```

The button uses a blue color scheme to indicate a modification action (distinct from destructive red for delete and informational gray for statistics).

## Known Limitations

1. **Side Panel Navigation**: Some Home Assistant installations may have restrictions on navigation from side panels. The multiple fallback methods minimize this issue.

2. **Config Entry Required**: The edit functionality requires that medications are created as separate config entries (one per medication). This is by design and enables individual medication configuration.

3. **No Inline Editing**: Currently, there's no inline editing on the cards themselves. All editing goes through Home Assistant's standard configuration UI. A future enhancement could add a modal-based inline editor.

## Future Enhancements

Potential improvements for future releases:

### Modal-Based Editor (Planned)
- Add a custom modal dialog for editing
- Show all fields directly in the Pill Assistant interface
- Eliminate the need to navigate away from the main view
- Provide a more seamless user experience

### Quick Edit Options
- Allow quick edits for common changes (dosage, schedule time)
- Add inline editing for simple text fields
- Provide validation and real-time feedback

### Batch Editing
- Allow editing multiple medications at once
- Useful for changing notification services or other common settings
- Provide templates for common medication configurations

## Troubleshooting

### Edit Button Not Working

**Problem**: Clicking Edit doesn't navigate to the configuration page

**Possible Causes:**
1. Panel not properly embedded in Home Assistant
2. Browser security restrictions blocking cross-frame navigation
3. Outdated Home Assistant version

**Solutions:**
1. Ensure the panel is accessed through Home Assistant's interface, not directly
2. Check browser console for navigation errors
3. Update Home Assistant to the latest version
4. Use the manual path: Settings → Devices & Services → Pill Assistant → Configure

### Changes Not Saving

**Problem**: Edit form shows but changes don't persist

**Possible Causes:**
1. Form validation errors
2. Backend storage issues
3. Concurrent modifications

**Solutions:**
1. Check for error messages in the form
2. Review Home Assistant logs for errors
3. Reload the page and try again
4. Restart Home Assistant if storage issues persist

## Related Documentation

- [Config Flow Implementation](custom_components/pill_assistant/config_flow.py) - The backend configuration logic
- [Options Flow Tests](tests/test_options_flow.py) - Comprehensive options flow testing
- [Edit Navigation Tests](tests/test_edit_medication_navigation.py) - Navigation-specific tests

## Conclusion

The edit button provides a reliable way to modify medication settings through Home Assistant's standard configuration interface. The implementation uses multiple fallback navigation methods to ensure compatibility across different Home Assistant setups and browser configurations.
