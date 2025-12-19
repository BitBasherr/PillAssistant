# Pill Assistant for Home Assistant

A comprehensive medication management integration for  
Home Assistant that helps you track medications, maintain  
schedules, and log medication history.

> **Note**: This README is optimized for both desktop and mobile viewing.

> **🎉 NEW**: Complete UI-based medication management! Add, edit, and delete medications directly from the frontend panel - **no YAML configuration required!**

## Features

### Core Features
- **Complete UI Management**: Add, edit, and delete medications from the frontend panel or Settings
  - ➕ **Add** medications with the "Add Medication" button
  - ✏️ **Edit** medications with the "Edit" button on each card
  - 🗑️ **Delete** medications with confirmation dialog
  - 🚫 **No YAML required** for any core functionality
- **Medication Management**: Manage multiple medications through the UI with PA_ entity naming prefix
- **Flexible Scheduling**: 
  - Fixed time schedules (specific times on specific days)
  - Relative scheduling (after another medication)
  - Sensor-based scheduling (after wake-up sensor, etc.)
  - Dynamic rebasing: schedules recalculate from actual taken times, not planned times
- **Dosage Tracking**: Track dosage amounts with various  
  unit options (pills, mL, mg, g, tablets, capsules, gelatin capsules, gummies, drops, sprays, puffs, syrup)
- **Refill Management**: 
  - Automatic alerts when medication supply is running low
  - Track remaining amount
  - Increment/decrement remaining amount via services
  - Adjust remaining doses through frontend panel with +/- buttons
  - One-click refill service
- **Real-time Status**: Sensor entities show current  
  medication status (scheduled, due, overdue, taken, refill needed)

### Logging and History
- **Persistent Logging**: All medication events (taken,  
  skipped, refilled) logged to a permanent CSV-style log file
- **Daily Tracking**: 
  - "Doses taken today" - list of timestamps for today's doses
  - "Taken/Scheduled ratio" - string format like "1/2" showing progress
- **Database Storage**: All medication data stored in  
  Home Assistant's database for real-time queries
- **Log File Location**: Displayed in sensor attributes for easy access

### Notifications and Actions
- **Test Notification Button**: Each medication gets a dedicated  
  test button (input_button helper) to verify notification setup
- **Actionable Notifications**: Mobile notifications include:
  - "Mark as Taken" button - automatically records medication taken
  - "Snooze" button (customizable duration per medication)
  - "Skip" button - logs skipped dose
  - Works with Home Assistant Companion App (iOS/Android)
- **Multiple Notification Services**: Select from available  
  notify.* services (e.g., mobile_app, telegram, etc.)

### Dosage Management
- **Dynamic Dosage Adjustment**: 
  - Increment/decrement dosage by 0.5 units via services
  - Adjust through frontend panel with +/- buttons
  - Update via options flow in UI
  - Minimum dosage of 0.5 units enforced
- **Dynamic Remaining Amount Adjustment**:
  - Increment/decrement remaining amount by dosage amount via services
  - Adjust through frontend panel with +/- buttons
  - Minimum remaining amount of 0 enforced
- **Flexible Units**: Support for pills, tablets, capsules, gelatin capsules, gummies, mL, mg, g,  
  drops, sprays, puffs, and syrup

### Frontend Panel
- **Web-based Control Panel**: Visual medication management interface
- **Real-time Status**: View all medications with current status
- **Quick Actions**: Mark taken, skip, refill, test notifications
- **Dosage Controls**: Increment/decrement with visual buttons
- **Responsive Design**: Works on desktop and mobile browsers

### Time Management
- **Flexible Time Input**: 
  - Native HA time selectors supported
  - Compact numeric entry (e.g., "1015" → "10:15")
  - AM/PM clarification for ambiguous times
  - Works in both config and options flows
- **Snooze Feature**:
  - Global default snooze duration (15 minutes)
  - Per-medication override available
  - Delays downstream medications appropriately

### UI and Configuration
- **UI Configuration**: Easy setup through Home Assistant UI  
  (no YAML required)
- **Options Flow**: Modify medication settings after creation
- **Human-Friendly Attributes**: Sensor attributes use readable  
  names like "Last taken at", "Medication ID", "Schedule"
- **Backward Compatibility**: Technical attribute keys preserved  
  for existing automations

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to Integrations
3. Click the three dots menu → "Custom repositories"
4. Add repository URL:  
   `https://github.com/BitBasherr/PillAssistant`
5. Category: Integration
6. Click "Add"
7. Search for "Pill Assistant" and click "Install"
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/pill_assistant` folder to your  
   Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Adding a Medication

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Pill Assistant"
4. Follow the setup wizard:
   - **Step 1**: Enter medication name, dosage amount,  
     dosage unit, and optional notes
   - **Step 2**: Set schedule times (e.g., "08:00", "20:00")  
     and days of week
   - **Step 3**: Configure refill amount, reminder threshold,  
     and optional notification services

### Modifying a Medication

1. Go to **Settings** → **Devices & Services**
2. Find your Pill Assistant integration
3. Click **Configure**
4. Update the settings as needed

## Sensor States

Each medication creates a sensor entity with the following possible states:

- **scheduled**: Next dose is scheduled but not yet due
- **due**: Medication is due to be taken  
  (within 30 minutes)
- **overdue**: Scheduled dose has been missed  
  (more than 30 minutes late)
- **taken**: Medication has been taken recently  
  (within last 6 hours)
- **refill_needed**: Remaining supply is below the  
  refill reminder threshold

## Sensor Attributes

Each sensor provides detailed attributes with human-friendly names:

### Display Attributes (Human-Friendly)
- `Medication ID`: Unique identifier for the medication
- `Dosage`: Combined dosage amount and unit (e.g., "100 mg")
- `Schedule`: Human-readable schedule string
  - Fixed time: "08:00, 20:00 on mon, tue, wed, thu, fri, sat, sun"
  - Relative: "2h 30m after MedicationA"
  - Sensor-based: "1h 0m after sensor.wake_up_time"
- `Remaining amount`: Current supply remaining
- `Last taken at`: Timestamp of last dose taken or "Never"
- `Next dose time`: Calculated next scheduled dose (ISO format)
- `Missed doses`: List of recent missed doses (last 5, within 24h)
- `Refill amount`: Full refill quantity
- `Refill reminder days`: Days threshold for refill reminder
- `Doses taken today`: List of times doses were taken today (e.g., ["08:15", "20:30"])
- `Taken/Scheduled ratio`: String showing daily progress (e.g., "1/2")
- `Log file location`: Full path to persistent log file
- `Notes`: Optional notes about the medication (if present)
- `Snooze until`: Active snooze end time (if snoozed)

### Legacy Attributes (For Backward Compatibility)
The following technical attribute keys are also available for existing automations:
- `remaining_amount`, `last_taken`, `dosage`, `dosage_unit`
- `next_dose_time`, `missed_doses`, `snooze_until`, `notes`

## Services

### pill_assistant.take_medication

Record that a medication has been taken. Decrements remaining  
amount and logs to history.

```yaml
service: pill_assistant.take_medication
data:
  # Get from sensor attributes
  medication_id: "abc123def456"
```

### pill_assistant.skip_medication

Record that a dose has been intentionally skipped.  
Logs to history without changing remaining amount.

```yaml
service: pill_assistant.skip_medication
data:
  medication_id: "abc123def456"
```

### pill_assistant.refill_medication

Reset medication count to full refill amount. Logs refill event to history.

```yaml
service: pill_assistant.refill_medication
data:
  medication_id: "abc123def456"
```

### pill_assistant.snooze_medication

Snooze a medication reminder for a specified duration (in minutes).

```yaml
service: pill_assistant.snooze_medication
data:
  medication_id: "abc123def456"
  snooze_duration: 15  # Optional, uses default if not specified
```

### pill_assistant.test_notification

Send a test notification for a medication to verify your notification setup.

```yaml
service: pill_assistant.test_notification
data:
  medication_id: "abc123def456"
```

### pill_assistant.increment_dosage

Increase medication dosage by 0.5 units. Useful for adjusting dosages without reconfiguring the medication.

```yaml
service: pill_assistant.increment_dosage
data:
  medication_id: "abc123def456"
```

### pill_assistant.decrement_dosage

Decrease medication dosage by 0.5 units (minimum 0.5). Useful for adjusting dosages without reconfiguring the medication.

```yaml
service: pill_assistant.decrement_dosage
data:
  medication_id: "abc123def456"
```

### pill_assistant.increment_remaining

Increase remaining medication amount by dosage amount. Useful for adjusting remaining supply without performing a full refill.

```yaml
service: pill_assistant.increment_remaining
data:
  medication_id: "abc123def456"
```

### pill_assistant.decrement_remaining

Decrease remaining medication amount by dosage amount (minimum 0). Useful for manually adjusting remaining supply.

```yaml
service: pill_assistant.decrement_remaining
data:
  medication_id: "abc123def456"
```

## Frontend Panel

A web-based control panel is available for **complete medication management** - no YAML configuration required!

### Accessing the Panel

The panel is **automatically registered** in your Home Assistant sidebar after installation. Look for the "Pill Assistant" menu item with a pill icon (🔵) in your sidebar.

Alternatively, you can access it directly at:

```
http://your-home-assistant:8123/pill_assistant/pill-assistant-panel.html
```

**Note**: The panel must be accessed from within Home Assistant (via sidebar or the URL above) to function properly. Direct browser access without the Home Assistant context will show a message with setup instructions.

The panel provides **full medication management**:
- **Add medications**: Click "Add Medication" button to create new medications
- **Edit medications**: Click "Edit" on any medication card to modify settings
- **Delete medications**: Click "Delete" on any medication card to remove medications
- **Visual medication cards** with status indicators
- **Quick actions**: Mark as taken, skip, refill, test notification
- **Dosage adjustment controls**: Increment/decrement dosage with +/- buttons
- **Real-time updates**: Automatically refreshes medication status
- **Responsive design**: Works on desktop and mobile devices

### Using the Frontend Panel

1. Click on **Pill Assistant** in your Home Assistant sidebar (or navigate to the URL above)
2. **Add medications**: Click the "Add Medication" button at the top
3. **View all medications** with their current status
4. **Edit medications**: Click the "Edit" button on any medication card
5. **Delete medications**: Click the "Delete" button on any medication card (with confirmation)
6. Use the **+** and **-** buttons to adjust dosages and remaining amounts
7. Click action buttons to:
   - **Mark as Taken**: Record that medication was taken
   - **Skip Dose**: Skip the current dose
   - **Refill**: Reset medication count to full amount
   - **Test Notification**: Send a test notification

**Everything can be managed from the panel - no Settings menu or YAML required!**

## Notification Actions

When you receive a medication reminder notification on your mobile device, you can interact with it directly:

- **Mark as Taken**: Automatically calls `pill_assistant.take_medication`
- **Snooze**: Automatically calls `pill_assistant.snooze_medication`
- **Skip**: Automatically calls `pill_assistant.skip_medication`

These actions work with:
- Home Assistant Companion App (iOS and Android)
- Other notification services that support actionable notifications

The notification actions are automatically set up when you configure notification services for a medication.

## Persistent Logging

All medication events are logged to **CSV files** in your Home Assistant configuration directory for easy analysis and record-keeping.

### Log File Locations

Logs are stored in: `config/Pill Assistant/Logs/`

- **Global log**: `pill_assistant_all_medications_log.csv` - Contains all events for all medications
- **Per-medication logs**: `{MedicationName}_log.csv` - Individual log file for each medication

**Finding Log Paths**: The full paths to both global and per-medication log files are displayed in each medication sensor's attributes:
- `Global log path`: Path to the combined log file
- `Medication log path`: Path to the medication-specific log file

### CSV Log Format

Each CSV log file contains the following columns:

- `timestamp`: When the event occurred (ISO format)
- `action`: Type of event (taken, skipped, refilled, snoozed, dosage_changed)
- `medication_id`: Unique identifier for the medication
- `medication_name`: Name of the medication
- `dosage`: Current dosage amount
- `dosage_unit`: Unit of measurement
- `remaining_amount`: Amount remaining after the event
- `refill_amount`: Total refill amount
- `snooze_until`: Snooze end time (if applicable)
- `details_json`: Additional event details in JSON format

### Example CSV Log Entries

```csv
timestamp,action,medication_id,medication_name,dosage,dosage_unit,remaining_amount,refill_amount,snooze_until,details_json
2025-12-15T08:00:45,taken,abc123,Aspirin,100,mg,89,90,,"{""timestamp"":""2025-12-15T08:00:45""}"
2025-12-15T20:15:30,skipped,def456,Vitamin D,2,pill(s),60,60,,"{""timestamp"":""2025-12-15T20:15:30""}"
2025-12-15T14:22:10,refilled,abc123,Aspirin,100,mg,90,90,,"{""timestamp"":""2025-12-15T14:22:10"",""amount"":90}"
```

These log files are permanent and survive Home Assistant restarts and updates, providing a complete auditable medication history. You can open them in Excel, Google Sheets, or any spreadsheet application for analysis.

## Automation Examples

### Send notification when medication is due

```yaml
automation:
  - alias: "Medication Due Notification"
    trigger:
      - platform: state
        entity_id: sensor.aspirin
        to: "due"
    action:
      - service: notify.mobile_app
        data:
          title: "Medication Reminder"
          message: >
            Time to take 
            {{ state_attr('sensor.aspirin', 'dosage') }}
            {{ state_attr('sensor.aspirin', 'dosage_unit') }}
            of Aspirin
```

### Auto-record medication when button pressed

```yaml
automation:
  - alias: "Record Medication via Button"
    trigger:
      - platform: state
        entity_id: input_button.took_aspirin
        to: "on"
    action:
      - service: pill_assistant.take_medication
        data:
          medication_id: >
            {{ state_attr(
              'sensor.aspirin',
              'medication_id'
            ) }}
```

### Alert when refill needed

```yaml
automation:
  - alias: "Refill Reminder"
    trigger:
      - platform: state
        entity_id: sensor.aspirin
        to: "refill_needed"
    action:
      - service: notify.mobile_app
        data:
          title: "Refill Reminder"
          message: >
            Aspirin is running low. Only
            {{ state_attr(
              'sensor.aspirin',
              'remaining_amount'
            ) }} remaining.
```

## YAML Configuration (Optional - Advanced Users Only)

**Important**: This integration is designed to be **completely UI-driven**. You can add, edit, and delete medications entirely from the UI (Frontend Panel or Settings → Devices & Services). **No YAML configuration is required for any core functionality.**

The YAML examples in the `examples/` directory are provided for **advanced users** who want to extend functionality with custom automations, helper entities, or template sensors. These are completely optional and not needed for the integration to work.

### What You Can Do Without YAML
- ✅ Add medications (Frontend Panel or Settings → Devices & Services)
- ✅ Edit medications (Frontend Panel or Settings → Devices & Services)
- ✅ Delete medications (Frontend Panel or Settings → Devices & Services)
- ✅ Take/Skip/Refill medications (Frontend Panel or Services)
- ✅ Adjust dosages (Frontend Panel)
- ✅ Test notifications (Frontend Panel)
- ✅ View medication status and history (Frontend Panel or Entity attributes)

### When You Might Want YAML (Optional)
- Creating custom automations for notifications
- Adding template sensors for advanced tracking
- Creating helper entities (input_button, input_boolean) for dashboard cards
- Setting up advanced Home Assistant automations

All medication data is stored using Home Assistant's storage API and persists across restarts. You can access medication data programmatically through entity attributes and service calls.

## Storage

- **Database**: Medication configurations and history  
  are stored in `.storage/pill_assistant.medications.json`
- **CSV Logs**: Persistent CSV log files stored in  
  `config/Pill Assistant/Logs/`
  - Global log: `pill_assistant_all_medications_log.csv`
  - Per-medication logs: `{MedicationName}_log.csv`

## Support

For issues, feature requests, or contributions:
- [GitHub Issues](https://github.com/BitBasherr/PillAssistant/issues)
- [GitHub Repository](https://github.com/BitBasherr/PillAssistant)

## License

This project is open source and available under the MIT License.

## Credits

Based on the Custom-Entity integration framework by  
[@BitBasherr](https://github.com/BitBasherr).
