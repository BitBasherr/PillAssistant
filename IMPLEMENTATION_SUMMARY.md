# Pill Assistant - New Features Summary

## Implemented Features

### 1. Duplicate Missed Doses Fix ✅
**Problem**: Missed doses were being reported multiple times for the same scheduled time.

**Solution**: Implemented set-based deduplication in `_get_missed_doses()` method to ensure each missed dose is only reported once.

**Testing**: Added comprehensive tests in `tests/test_missed_doses.py`:
- Test for no duplicate doses
- Test for 24-hour window enforcement
- Test for respecting last taken time
- Test for chronological sorting

### 2. Test Notification Button ✅
**Feature**: Optional input_button helper creation for each medication to test notifications.

**Implementation**:
- Added `create_test_button` option in config flow (refill step)
- Added `create_test_button` option in options flow
- Button creation attempts to call `input_button.create` service
- Gracefully handles failures (logs warning but doesn't fail setup)

**Testing**: Added tests in `tests/test_config_flow.py` and `tests/test_options_flow.py`

### 3. Test Notification Service ✅
**Feature**: `pill_assistant.test_notification` service to send test notifications.

**Implementation**:
- Sends notifications via configured notification services
- Falls back to persistent_notification if no services configured
- Includes Android Actions in notification data:
  - "Mark as Taken" action
  - "Skip" action
- Compatible with mobile apps and Android Auto

**Usage Example**:
```yaml
service: pill_assistant.test_notification
data:
  medication_id: "01KCH061WB0MQ3CP0Q8FBY4E5E"
```

**Testing**: Added tests in `tests/test_notifications.py`

### 4. Snooze/Delay Functionality ✅
**Feature**: `pill_assistant.snooze_medication` service to delay medication reminders.

**Implementation**:
- Configurable snooze duration (default: 15 minutes)
- Stores snooze_until timestamp in medication data
- Sensor respects snooze - won't mark as "due" or "overdue" when snoozed
- Automatically clears expired snooze periods
- Adds `snooze_until` attribute to sensor when active

**Usage Example**:
```yaml
service: pill_assistant.snooze_medication
data:
  medication_id: "01KCH061WB0MQ3CP0Q8FBY4E5E"
  snooze_duration: 30  # minutes (optional, defaults to 15)
```

**Testing**: Added comprehensive tests in `tests/test_snooze.py`

### 5. Android Actions Support ✅
**Feature**: Notification actions compatible with Android mobile apps.

**Implementation**:
- Test notification service includes action buttons
- Actions include unique identifiers based on medication ID
- Compatible with Home Assistant mobile app on Android
- Can be extended to Android Auto with configuration

## Automation Examples

### Complete Medication Management Automation

```yaml
# Automation to send notification when medication is due
automation:
  - alias: "Medication Due - Send Notification"
    trigger:
      - platform: state
        entity_id: sensor.aspirin
        to: "due"
    action:
      - service: pill_assistant.test_notification
        data:
          medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"

  - alias: "Test Button Pressed - Send Test Notification"
    trigger:
      - platform: state
        entity_id: input_button.test_aspirin_notification
    action:
      - service: pill_assistant.test_notification
        data:
          medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"

  - alias: "Snooze Medication from Notification Action"
    trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: "snooze_medication_{{ state_attr('sensor.aspirin', 'medication_id') }}"
    action:
      - service: pill_assistant.snooze_medication
        data:
          medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"
          snooze_duration: 15

  - alias: "Mark as Taken from Notification Action"
    trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: "take_medication_{{ state_attr('sensor.aspirin', 'medication_id') }}"
    action:
      - service: pill_assistant.take_medication
        data:
          medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"
```

## Remaining Work (As Per Problem Statement)

### Advanced Scheduling Features (Partially Started)
Constants and data structures added, but implementation pending:
- [ ] Medication dependencies (take X hours after another medication)
- [ ] Sensor-based scheduling (take after wake-up sensor triggers)
- [ ] Config flow UI for relative scheduling
- [ ] Circular dependency validation

### Enhanced Notifications
- [x] Android Actions (implemented in test_notification)
- [ ] Research HA 2025.12 specific notification features
- [ ] Enhanced toast notifications
- [ ] Android Auto specific configuration
- [ ] Platform-specific testing

### Documentation
- [ ] Update README with new features
- [ ] Add automation examples
- [ ] Document snooze functionality
- [ ] Document test notification button
- [ ] Add troubleshooting guide

## Technical Notes

### New Constants Added
```python
# Services
SERVICE_TEST_NOTIFICATION
SERVICE_SNOOZE_MEDICATION

# Attributes
ATTR_SNOOZE_UNTIL
ATTR_SNOOZE_DURATION

# Config
CONF_CREATE_TEST_BUTTON
CONF_SNOOZE_DURATION_MINUTES
CONF_SCHEDULE_TYPE
CONF_RELATIVE_TO_MEDICATION
CONF_RELATIVE_TO_SENSOR
CONF_RELATIVE_OFFSET_HOURS
CONF_RELATIVE_OFFSET_MINUTES
```

### Storage Schema Updates
Medication data now includes:
- `snooze_until`: ISO timestamp when snooze expires (optional)

### Sensor States
Snooze affects state calculation:
- Snoozed medications show as "scheduled" even if time would indicate "due" or "overdue"
- Snooze automatically expires and clears when timestamp passes

## Testing Summary

**Total Tests**: 30
**All Passing**: ✅

Test Coverage:
- Config flow (6 tests)
- Options flow (6 tests)
- Services (7 tests)
- Missed doses (4 tests)
- Notifications (2 tests)
- Snooze functionality (3 tests)
- Integration setup (2 tests)

## Breaking Changes

**None** - All changes are backward compatible. Existing medications continue to work without modification.
