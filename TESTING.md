# Testing Checklist for Pill Assistant

This document provides a comprehensive testing checklist for the Pill Assistant integration.

## Pre-Installation Testing

### Environment Preparation
- [ ] Home Assistant version 2024.6.0 or newer
- [ ] Test instance or backup of production instance
- [ ] Access to Home Assistant configuration directory
- [ ] Developer Tools enabled

## Installation Testing

### HACS Installation (Recommended)
- [ ] HACS is installed and configured
- [ ] Can access HACS → Integrations
- [ ] Can add custom repository
- [ ] Repository URL accepted: `https://github.com/BitBasherr/PillAssistant`
- [ ] Integration appears in search
- [ ] Download completes successfully
- [ ] Restart Home Assistant completes

### Manual Installation
- [ ] `custom_components` directory exists
- [ ] Can copy `pill_assistant` folder
- [ ] File permissions are correct
- [ ] Restart Home Assistant completes
- [ ] No errors in Home Assistant log

## Configuration Testing

### Initial Setup - Step 1: Medication Details
- [ ] Integration appears in "Add Integration" search
- [ ] Can click on Pill Assistant integration
- [ ] Step 1 form displays correctly
- [ ] Medication name field accepts input
- [ ] Dosage amount field accepts numbers
- [ ] Dosage unit dropdown shows all 9 options
- [ ] Notes field accepts text (optional)
- [ ] Required field validation works
- [ ] Can proceed to Step 2

### Step 2: Schedule Configuration
- [ ] Step 2 form displays correctly
- [ ] Can enter multiple times (e.g., "08:00", "20:00")
- [ ] Time format validation works
- [ ] Days of week multi-select works
- [ ] Can select individual days
- [ ] Can select all days
- [ ] Default is all 7 days
- [ ] Can proceed to Step 3

### Step 3: Refill Settings
- [ ] Step 3 form displays correctly
- [ ] Refill amount accepts positive integers
- [ ] Refill reminder days accepts positive integers
- [ ] Defaults are set (30 and 7)
- [ ] Can complete setup
- [ ] Integration entry created
- [ ] Success message appears

### Post-Configuration
- [ ] Medication appears in Integrations list
- [ ] Entry shows medication name as title
- [ ] Can click Configure to modify settings
- [ ] Integration entry has unique ID

## Entity Testing

### Sensor Entity Creation
- [ ] Sensor entity appears in entity list
- [ ] Entity ID format: `sensor.medication_name`
- [ ] Entity has correct friendly name
- [ ] Entity shows initial state
- [ ] Entity has unique ID

### Sensor States
- [ ] Initial state is "scheduled"
- [ ] State changes to "due" within 30 min of scheduled time
- [ ] State changes to "overdue" after missed dose
- [ ] State changes to "taken" after service call
- [ ] State changes to "refill_needed" when supply low
- [ ] State transitions happen automatically

### Sensor Icons
- [ ] Icon is calendar-clock for "scheduled"
- [ ] Icon is pill for "due"
- [ ] Icon is alert-circle for "overdue"
- [ ] Icon is check-circle for "taken"
- [ ] Icon is package-variant for "refill_needed"

### Sensor Attributes
- [ ] `medication_id` attribute exists
- [ ] `dosage` attribute shows correct value
- [ ] `dosage_unit` attribute shows correct unit
- [ ] `schedule` attribute has times and days
- [ ] `remaining_amount` attribute shows count
- [ ] `last_taken` attribute updates after take
- [ ] `next_dose_time` attribute calculates correctly
- [ ] `missed_doses` attribute lists recent misses
- [ ] `refill_amount` attribute shows full amount
- [ ] `refill_reminder_days` attribute shows threshold
- [ ] `notes` attribute shows entered notes

## Service Testing

### Service Discovery
- [ ] Services appear in Developer Tools → Services
- [ ] `pill_assistant.take_medication` is listed
- [ ] `pill_assistant.skip_medication` is listed
- [ ] `pill_assistant.refill_medication` is listed
- [ ] Service descriptions are clear

### Take Medication Service
- [ ] Can call service from Developer Tools
- [ ] Requires `medication_id` parameter
- [ ] Service executes successfully
- [ ] `remaining_amount` decreases by 1
- [ ] `last_taken` timestamp updates
- [ ] State changes to "taken"
- [ ] History entry added to database
- [ ] Log entry added to text file
- [ ] Log format is correct
- [ ] Error handling works for invalid ID

### Skip Medication Service
- [ ] Can call service from Developer Tools
- [ ] Requires `medication_id` parameter
- [ ] Service executes successfully
- [ ] `remaining_amount` stays the same
- [ ] History entry added to database
- [ ] Log entry added to text file
- [ ] Log format is correct

### Refill Medication Service
- [ ] Can call service from Developer Tools
- [ ] Requires `medication_id` parameter
- [ ] Service executes successfully
- [ ] `remaining_amount` resets to `refill_amount`
- [ ] History entry added to database
- [ ] Log entry added to text file
- [ ] Log format is correct
- [ ] State updates appropriately

## Storage Testing

### Database Storage
- [ ] `.storage/pill_assistant.medications.json` created
- [ ] File is valid JSON
- [ ] Contains medications object
- [ ] Contains history array
- [ ] Data persists after restart
- [ ] Multiple medications stored correctly
- [ ] Updates are atomic

### Persistent Log File
- [ ] `pill_assistant_history.log` created in config directory
- [ ] File is plain text
- [ ] Entries are human-readable
- [ ] Timestamp format is correct
- [ ] All events logged (TAKEN, SKIPPED, REFILLED)
- [ ] File survives restart
- [ ] File permissions are correct
- [ ] Can be viewed in text editor

## Schedule Testing

### Time-Based Scheduling
- [ ] Single time per day works
- [ ] Multiple times per day work
- [ ] Time format HH:MM validated
- [ ] Next dose time calculated correctly
- [ ] Due window (30 min before) works
- [ ] Overdue detection (30 min after) works

### Day-Based Scheduling
- [ ] Single day per week works
- [ ] Multiple days work
- [ ] All 7 days work
- [ ] Day abbreviations correct (mon, tue, etc.)
- [ ] Today's schedule recognized
- [ ] Tomorrow's schedule recognized
- [ ] Week-long calculations work

### Combined Schedule Testing
- [ ] Multiple times + multiple days work together
- [ ] Next dose calculation spans days correctly
- [ ] Missed dose detection works across days
- [ ] Schedule respects both time and day constraints

## Refill Testing

### Supply Tracking
- [ ] Initial amount set from config
- [ ] Amount decreases with each dose
- [ ] Amount never goes below 0
- [ ] Amount resets on refill
- [ ] Floating point math is accurate

### Refill Reminder Logic
- [ ] Calculates doses per day correctly
- [ ] Calculates days remaining correctly
- [ ] Triggers refill_needed state at threshold
- [ ] Threshold configurable (default 7 days)
- [ ] Works with varying schedules

## Options Flow Testing

### Accessing Options
- [ ] Can click Configure on integration entry
- [ ] Options form displays
- [ ] Current values pre-filled
- [ ] All fields editable

### Modifying Settings
- [ ] Can change medication name
- [ ] Can change dosage amount
- [ ] Can change dosage unit
- [ ] Can change schedule times
- [ ] Can change schedule days
- [ ] Can change refill amount
- [ ] Can change refill reminder days
- [ ] Can change notes
- [ ] Changes save successfully
- [ ] Entity updates after changes
- [ ] No restart required

## Multiple Medications Testing

### Adding Multiple Medications
- [ ] Can add 2nd medication
- [ ] Can add 3rd medication
- [ ] Each gets unique entity ID
- [ ] Each gets unique medication_id
- [ ] Each tracked independently
- [ ] No cross-contamination of data

### Managing Multiple Medications
- [ ] All medications visible in entity list
- [ ] All medications in integrations list
- [ ] Services work for each medication
- [ ] Storage handles multiple entries
- [ ] Log entries distinguish medications

## Dashboard Integration Testing

### Entity Card
- [ ] Can add to dashboard
- [ ] Entity card displays correctly
- [ ] Shows current state
- [ ] Shows secondary info
- [ ] Icon displays correctly

### Entities Card
- [ ] Can add multiple medications
- [ ] List displays cleanly
- [ ] Can sort by state
- [ ] Can filter by state

### Button Card
- [ ] Can create button cards for services
- [ ] Tap actions work
- [ ] Service calls execute
- [ ] Visual feedback works

## Automation Testing

### State-Based Triggers
- [ ] Trigger on "due" state
- [ ] Trigger on "overdue" state
- [ ] Trigger on "taken" state
- [ ] Trigger on "refill_needed" state
- [ ] Multiple automations can trigger
- [ ] Automation logs show triggers

### Attribute-Based Conditions
- [ ] Can use remaining_amount in conditions
- [ ] Can use next_dose_time in conditions
- [ ] Can use missed_doses in conditions
- [ ] Template conditions work

### Service Actions
- [ ] Automation can call take_medication
- [ ] Automation can call skip_medication
- [ ] Automation can call refill_medication
- [ ] Template data works for medication_id

## Notification Testing

### Basic Notifications
- [ ] Notification sent on due
- [ ] Notification sent on overdue
- [ ] Notification sent on refill_needed
- [ ] Message includes medication name
- [ ] Message includes dosage info

### Advanced Notifications
- [ ] Action buttons work
- [ ] Clicking action triggers automation
- [ ] take_medication called from notification
- [ ] skip_medication called from notification
- [ ] Persistent notifications work

## Edge Cases Testing

### Invalid Input
- [ ] Empty medication name rejected
- [ ] Invalid time format rejected
- [ ] Negative dosage rejected
- [ ] Negative refill amount rejected
- [ ] Invalid medication_id handled gracefully

### Boundary Conditions
- [ ] Zero remaining amount handled
- [ ] Maximum refill amount handled
- [ ] Very short schedule intervals work
- [ ] Very long schedule intervals work
- [ ] Midnight crossing works correctly

### Error Conditions
- [ ] Missing medication_id in service call
- [ ] Corrupted storage file recovery
- [ ] Log file permission errors handled
- [ ] Multiple simultaneous updates handled
- [ ] Restart during service call handled

## Performance Testing

### Response Time
- [ ] Entity updates within 1 minute
- [ ] Service calls respond quickly (<1 sec)
- [ ] UI loads quickly
- [ ] No lag in automations

### Resource Usage
- [ ] CPU usage reasonable
- [ ] Memory usage reasonable
- [ ] Log file size manageable
- [ ] No memory leaks over time

## Documentation Testing

### README Accuracy
- [ ] Installation instructions work
- [ ] Configuration steps accurate
- [ ] Service examples work
- [ ] Automation examples work
- [ ] Attribute names correct

### Quick Start Guide
- [ ] All steps can be followed
- [ ] Examples work as described
- [ ] No missing information
- [ ] Beginners can complete setup

### Automation Examples
- [ ] All 12+ examples are valid
- [ ] YAML syntax correct
- [ ] Entity IDs are placeholders
- [ ] Examples cover common use cases

## Upgrade Testing

### Data Preservation
- [ ] Existing medications preserved
- [ ] History preserved
- [ ] Log file preserved
- [ ] Entity IDs unchanged
- [ ] Automation compatibility maintained

## Uninstall Testing

### Clean Removal
- [ ] Can delete integration entry
- [ ] Entities removed
- [ ] Services unregistered
- [ ] Storage file can be deleted
- [ ] Log file can be deleted
- [ ] No orphaned data

## Security Testing

### CodeQL Results
- [ ] No security alerts
- [ ] No vulnerable dependencies
- [ ] No hardcoded secrets
- [ ] No SQL injection vectors
- [ ] No file traversal vectors

### Data Privacy
- [ ] No external API calls
- [ ] No telemetry
- [ ] Data stays local
- [ ] No unencrypted network traffic
- [ ] Log files secured appropriately

## Accessibility Testing

### UI Accessibility
- [ ] Labels are descriptive
- [ ] Form fields have labels
- [ ] Error messages are clear
- [ ] Help text is available
- [ ] Navigation is logical

## Cross-Platform Testing

### Different HA Installations
- [ ] Works on HA OS
- [ ] Works on HA Container
- [ ] Works on HA Core
- [ ] Works on HA Supervised

## Test Results Summary

**Date Tested**: ___________  
**Tester Name**: ___________  
**HA Version**: ___________  
**Test Environment**: ___________  

**Total Tests**: ___________  
**Tests Passed**: ___________  
**Tests Failed**: ___________  
**Tests Skipped**: ___________  

**Critical Issues Found**: ___________  
**Minor Issues Found**: ___________  

**Overall Status**: [ ] PASS [ ] FAIL [ ] NEEDS WORK

**Notes**:
_______________________________________________________________________________
_______________________________________________________________________________
_______________________________________________________________________________
