# Pill Assistant for Home Assistant

A comprehensive medication management integration for Home Assistant that helps you track medications, maintain schedules, and log medication history.

## Features

- **Medication Management**: Add and manage multiple medications through the UI
- **Flexible Scheduling**: Configure time of day and days of week for each medication
- **Dosage Tracking**: Track dosage amounts with various unit options (pills, mL, mg, etc.)
- **Refill Reminders**: Automatic alerts when medication supply is running low
- **Persistent Logging**: All medication events (taken, skipped, refilled) are logged to a persistent file
- **Real-time Status**: Sensor entities show current medication status (scheduled, due, overdue, taken, refill needed)
- **Database Storage**: All medication data stored in Home Assistant's database
- **Service Calls**: Control medications via automations using service calls
- **UI Configuration**: Easy setup through Home Assistant UI (no YAML required)
- **Options Flow**: Modify medication settings after creation

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to Integrations
3. Click the three dots menu and select "Custom repositories"
4. Add repository URL: `https://github.com/BitBasherr/PillAssistant`
5. Category: Integration
6. Click "Add"
7. Search for "Pill Assistant" and click "Install"
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/pill_assistant` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Adding a Medication

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Pill Assistant"
4. Follow the setup wizard:
   - **Step 1**: Enter medication name, dosage amount, dosage unit, and optional notes
   - **Step 2**: Set schedule times (e.g., "08:00", "20:00") and days of week
   - **Step 3**: Configure refill amount, reminder threshold, and optional notification services

### Modifying a Medication

1. Go to **Settings** → **Devices & Services**
2. Find your Pill Assistant integration
3. Click **Configure**
4. Update the settings as needed

## Sensor States

Each medication creates a sensor entity with the following possible states:

- **scheduled**: Next dose is scheduled but not yet due
- **due**: Medication is due to be taken (within 30 minutes)
- **overdue**: Scheduled dose has been missed (more than 30 minutes late)
- **taken**: Medication has been taken recently (within last 6 hours)
- **refill_needed**: Remaining supply is below the refill reminder threshold

## Sensor Attributes

Each sensor provides detailed attributes:

- `medication_id`: Unique identifier for the medication
- `dosage`: Amount to take
- `dosage_unit`: Unit of measurement
- `schedule`: Times and days configured
- `remaining_amount`: Current supply remaining
- `last_taken`: Timestamp of last dose taken
- `next_dose_time`: Calculated next scheduled dose
- `missed_doses`: List of recent missed doses
- `refill_amount`: Full refill quantity
- `refill_reminder_days`: Days threshold for refill reminder
- `notes`: Optional notes about the medication
- `notify_services`: List of configured notification services (optional)

## Services

### pill_assistant.take_medication

Record that a medication has been taken. Decrements remaining amount and logs to history.

```yaml
service: pill_assistant.take_medication
data:
  medication_id: "abc123def456"  # Get from sensor attributes
```

### pill_assistant.skip_medication

Record that a dose has been intentionally skipped. Logs to history without changing remaining amount.

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

## Persistent Logging

All medication events are logged to `pill_assistant_history.log` in your Home Assistant configuration directory. Each line includes:

- Timestamp
- Action (TAKEN, SKIPPED, REFILLED)
- Medication name
- Dosage information (for taken events)

Example log entries:
```
2025-12-15 08:00:45 - TAKEN - Aspirin - 100 mg
2025-12-15 20:15:30 - SKIPPED - Vitamin D
2025-12-15 14:22:10 - REFILLED - Aspirin - 90 units
```

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
          message: "Time to take {{ state_attr('sensor.aspirin', 'dosage') }} {{ state_attr('sensor.aspirin', 'dosage_unit') }} of Aspirin"
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
          medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"
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
          message: "Aspirin is running low. Only {{ state_attr('sensor.aspirin', 'remaining_amount') }} remaining."
```

## YAML Configuration (Optional)

While the integration is designed for UI configuration, you can also access medication data programmatically. The integration stores all data using Home Assistant's storage API, which persists across restarts.

## Storage

- **Database**: Medication configurations and history are stored in `.storage/pill_assistant.medications.json`
- **Log File**: Persistent text log stored in `pill_assistant_history.log`

## Support

For issues, feature requests, or contributions:
- GitHub Issues: https://github.com/BitBasherr/PillAssistant/issues
- GitHub Repository: https://github.com/BitBasherr/PillAssistant

## License

This project is open source and available under the MIT License.

## Credits

Based on the Custom-Entity integration framework by @BitBasherr.
