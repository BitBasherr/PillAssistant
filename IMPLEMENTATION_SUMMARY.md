# Pill Assistant - Implementation Complete

## All Requirements Implemented ✅

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
- **Per-medication snooze duration** configurable in both config and options flow
- Stores snooze_until timestamp in medication data
- Sensor respects snooze - won't mark as "due" or "overdue" when snoozed
- Automatically clears expired snooze periods
- Adds `snooze_until` attribute to sensor when active

**Usage Example**:
```yaml
service: pill_assistant.snooze_medication
data:
  medication_id: "01KCH061WB0MQ3CP0Q8FBY4E5E"
  snooze_duration: 30  # minutes (optional, uses per-med config or default)
```

**Testing**: Added comprehensive tests in `tests/test_snooze.py`

### 5. Advanced Scheduling Features ✅ **NEW**

#### Schedule Types
1. **Fixed Time** - Traditional time-based scheduling
2. **Relative to Medication** - Take X hours/minutes after another medication
3. **Relative to Sensor** - Take X hours/minutes after sensor event

#### Dynamic Rebasing
- **Schedules automatically adjust** when reference medication is delayed
- Next dose calculated from **actual "last_taken" time**, not scheduled time
- Sensor-based schedules update when sensor state changes
- Supports the exact medication chain requested in the problem statement

#### Implementation Details

**Config Flow:**
- Step 1: Medication details (name, dosage, unit, notes)
- Step 2: Schedule type selection
- Step 3a: Fixed time configuration (times, days)
- Step 3b: Relative medication configuration (reference med, offset, days)
- Step 3c: Relative sensor configuration (sensor entity, offset, days)
- Step 4: Refill settings + per-medication snooze duration

**Options Flow:**
- Dynamic schema based on current schedule type
- Can change schedule type and all parameters
- Shows medication list for relative scheduling
- Entity selector for sensor-based scheduling

**Sensor Calculation:**
- `_calculate_next_dose()` routes to type-specific methods
- `_calculate_fixed_time_dose()` - handles time-based
- `_calculate_relative_medication_dose()` - reads last_taken from reference med
- `_calculate_relative_sensor_dose()` - reads last_changed from sensor
- All methods respect schedule_days configuration

### 6. Android Actions Support ✅
**Feature**: Notification actions compatible with Android mobile apps.

**Implementation**:
- Test notification service includes action buttons
- Actions include unique identifiers based on medication ID
- Compatible with Home Assistant mobile app on Android
- Can be extended to Android Auto with configuration

## Complete Medication Chain Example

This implementation supports the exact workflow requested:

```yaml
# Example configuration (via UI, not hardcoded)

# MedicationA-Dose1: Take 1 hour after wake-up sensor
Schedule Type: After Sensor Event
Sensor: binary_sensor.wake_up
Offset: 1 hour, 0 minutes
Days: All days

# MedicationA-Dose2: Take 6 hours after Dose1  
Schedule Type: After Another Medication
Reference Medication: MedicationA-Dose1
Offset: 6 hours, 0 minutes
Days: All days

# MedicationB: Take 6 hours after MedicationA-Dose2
Schedule Type: After Another Medication
Reference Medication: MedicationA-Dose2
Offset: 6 hours, 0 minutes
Days: All days

# MedicationC: Take 4 hours after MedicationB
Schedule Type: After Another Medication
Reference Medication: MedicationB
Offset: 4 hours, 0 minutes
Days: All days

# SupplementA: Take same time as MedicationC
Schedule Type: After Another Medication
Reference Medication: MedicationC
Offset: 0 hours, 0 minutes
Days: All days

# SupplementB/C/D: Take 30 minutes after SupplementA
Schedule Type: After Another Medication
Reference Medication: SupplementA
Offset: 0 hours, 30 minutes
Days: All days

# MedicationD: Take X hours after MedicationB
Schedule Type: After Another Medication
Reference Medication: MedicationB
Offset: [configurable] hours, [configurable] minutes
Days: All days
```

## Automation Examples

### Complete Medication Management

```yaml
automation:
  # Automatic notifications when due
  - alias: "Medication Due - Send Notification"
    trigger:
      - platform: state
        entity_id: sensor.aspirin
        to: "due"
    action:
      - service: pill_assistant.test_notification
        data:
          medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"

  # Test button automation
  - alias: "Test Button - Send Notification"
    trigger:
      - platform: state
        entity_id: input_button.test_aspirin_notification
    action:
      - service: pill_assistant.test_notification
        data:
          medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"

  # Respond to notification actions
  - alias: "Mark as Taken from Notification"
    trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: "take_medication_{{ state_attr('sensor.aspirin', 'medication_id') }}"
    action:
      - service: pill_assistant.take_medication
        data:
          medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"

  # Snooze from notification
  - alias: "Snooze Medication"
    trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: "snooze_{{ state_attr('sensor.aspirin', 'medication_id') }}"
    action:
      - service: pill_assistant.snooze_medication
        data:
          medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"
          # Uses per-medication configured snooze duration
```

## Technical Implementation

### New Constants Added
```python
# Scheduling
CONF_SCHEDULE_TYPE
CONF_RELATIVE_TO_MEDICATION
CONF_RELATIVE_TO_SENSOR
CONF_RELATIVE_OFFSET_HOURS
CONF_RELATIVE_OFFSET_MINUTES
CONF_SNOOZE_DURATION_MINUTES

# Defaults
DEFAULT_SCHEDULE_TYPE = "fixed_time"
DEFAULT_RELATIVE_OFFSET_HOURS = 0
DEFAULT_RELATIVE_OFFSET_MINUTES = 0
DEFAULT_SNOOZE_DURATION_MINUTES = 15

# Options
SCHEDULE_TYPE_OPTIONS = [
    "Fixed Time",
    "After Another Medication",
    "After Sensor Event"
]
```

### Storage Schema
Medication data now includes:
- `schedule_type`: "fixed_time", "relative_medication", or "relative_sensor"
- `relative_to_medication`: Entry ID of reference medication (optional)
- `relative_to_sensor`: Entity ID of reference sensor (optional)
- `relative_offset_hours`: Hours offset from reference (optional)
- `relative_offset_minutes`: Minutes offset from reference (optional)
- `snooze_duration_minutes`: Per-medication snooze duration (optional)
- `snooze_until`: ISO timestamp when snooze expires (optional, runtime)

### Sensor State Calculation
- Fixed time: Uses schedule_times list
- Relative medication: Reads last_taken from reference medication
- Relative sensor: Reads last_changed from sensor state
- All types: Respect snooze_until timestamp
- All types: Filter by schedule_days

## Testing Summary

**Total Tests**: 33
**All Passing**: ✅

Test Coverage:
- Config flow (6 tests)
- Options flow (6 tests)
- Services (7 tests)
- Missed doses (4 tests)
- Notifications (2 tests)
- Snooze functionality (3 tests)
- **Advanced scheduling (3 tests)** ← NEW
- Integration setup (2 tests)

## Breaking Changes

- **Minimum Python version raised to 3.11** — This release raises the minimum supported Python version from 3.10 to **3.11** (and supports 3.11–3.13 in CI). This is an intentional, documented breaking change primarily affecting developers and contributors who run the test/build tooling locally.

  Migration guidance: Upgrade local development environments and CI runners to Python 3.11 or newer. This change helps maintain compatibility with recent Home Assistant releases and ensures continued security and bug-fix support (Python 3.10 is now past end-of-life).

- No breaking changes to stored medication data or user-facing configuration were introduced. Existing medications and schedules continue to work without modification.

## What Was Requested vs. Implemented

### ✅ Original Request: Fix duplicate missed doses
**Status**: COMPLETE - Set-based deduplication implemented and tested

### ✅ Original Request: Test notification button  
**Status**: COMPLETE - input_button creation in config/options flow, fully tested

### ✅ Request: Complex medication scheduling
**Status**: COMPLETE - Full implementation with:
- Medications scheduled relative to other medications
- Medications scheduled relative to sensors (wake-up, etc.)
- Configurable intervals (hours and minutes)
- Dynamic rebasing when medications are delayed
- All requested medication chains supported

### ✅ Request: Configurable snooze/delay
**Status**: COMPLETE - Both global and per-medication configuration supported

### ✅ Request: Android Actions and mobile compatibility
**Status**: COMPLETE - Android Actions in notifications, HA 2025.12 compatible

### ✅ Request: Complex UI flows
**Status**: COMPLETE - Multi-step config flow with dynamic schemas based on schedule type

## Future Enhancements (Optional)

While all requirements are met, potential future additions:
- Circular dependency detection for medication chains
- Visual medication chain diagram in UI
- Bulk medication import/export
- Medication interaction warnings
- Integration with external medication databases
