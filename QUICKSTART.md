# Quick Start Guide for Pill Assistant

This guide will help you get started with Pill Assistant in just a few minutes.

> **🎉 NEW**: You can now manage medications entirely from the UI! No YAML configuration required!

## Step 1: Installation

### Option A: HACS (Recommended)
1. Open Home Assistant
2. Go to HACS → Integrations
3. Click the three dots (⋮) → Custom repositories
4. Add: `https://github.com/BitBasherr/PillAssistant`
5. Category: Integration
6. Search for "Pill Assistant" and click Install
7. Restart Home Assistant

### Option B: Manual
1. Copy `custom_components/pill_assistant` folder to your HA config directory
2. Restart Home Assistant

## Step 2: Add Your First Medication

### Option A: Using the Frontend Panel (Easiest! ⭐)
1. Click **Pill Assistant** in your Home Assistant sidebar
2. Click the **"➕ Add Medication"** button
3. Follow the setup wizard

### Option B: Using Settings Menu
1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Pill Assistant"
4. Follow the 3-step wizard:

### Step 1: Medication Details
- **Medication Name**: e.g., "Aspirin"
- **Dosage Amount**: e.g., "100"
- **Dosage Unit**: e.g., "mg"
- **Notes**: Optional notes about the medication

### Step 2: Schedule
- **Times to Take**: e.g., "08:00" and "20:00" (one per line or comma-separated)
- **Days of Week**: Select the days (default is all 7 days)

### Step 3: Refill Settings
- **Initial/Refill Amount**: e.g., "90" (how many doses per refill)
- **Days Before Refill Reminder**: e.g., "7" (when to remind you to refill)

Click **Submit** and your medication is ready!

## Step 3: View Your Medication

Your medication now appears as a sensor entity in Home Assistant:
- Entity ID: `sensor.aspirin` (or similar based on medication name)
- State: Shows current status (scheduled, due, overdue, taken, refill_needed)

### Add to Dashboard

Create a simple dashboard card:

```yaml
type: entities
title: My Medications
entities:
  - sensor.aspirin
```

## Step 4: Mark Medication as Taken

### Option A: Using Services (Developer Tools)
1. Go to **Developer Tools** → **Services**
2. Select service: `pill_assistant.take_medication`
3. Enter data:
```yaml
medication_id: "abc123..."  # Get from sensor attributes
```

### Option B: Create a Button (Recommended)

Add to `configuration.yaml`:
```yaml
input_button:
  took_aspirin:
    name: "Took Aspirin"
    icon: mdi:pill
```

Then create an automation:
```yaml
automation:
  - alias: "Record Aspirin Taken"
    trigger:
      - platform: state
        entity_id: input_button.took_aspirin
    action:
      - service: pill_assistant.take_medication
        data:
          medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"
```

## Step 5: Set Up Notifications

Create a basic notification automation:

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
          title: "💊 Medication Reminder"
          message: "Time to take your Aspirin"
```

## Understanding Sensor States

- **scheduled**: Medication is scheduled but not due yet
- **due**: Time to take medication (within 30 minutes of scheduled time)
- **overdue**: Missed scheduled dose (more than 30 minutes late)
- **taken**: Recently taken (within last 6 hours)
- **refill_needed**: Supply is running low

## Viewing History

All medication events are logged to `pill_assistant_history.log` in your Home Assistant config directory.

Example log entries:
```
2025-12-15 08:00:45 - TAKEN - Aspirin - 100 mg
2025-12-15 20:15:30 - SKIPPED - Vitamin D
2025-12-15 14:22:10 - REFILLED - Aspirin - 90 units
```

## Common Tasks

### Add Another Medication
**Easy way**: Click "➕ Add Medication" button in the Frontend Panel  
**Alternative**: Repeat Step 2 via Settings → Devices & Services

### Modify Medication Settings
**Easy way**: Click "✏️ Edit" button on the medication card in Frontend Panel  
**Alternative**:
1. Go to **Settings** → **Devices & Services**
2. Find Pill Assistant integration
3. Click **Configure** on the medication entry
4. Update settings and save

### Delete a Medication
**Easy way**: Click "🗑️ Delete" button on the medication card in Frontend Panel (with confirmation)  
**Alternative**:
1. Go to **Settings** → **Devices & Services**
2. Find Pill Assistant integration
3. Click on the medication entry
4. Click **Delete**

### Check Remaining Supply
View the `remaining_amount` attribute in the sensor's attributes

### Manual Refill
Use the `pill_assistant.refill_medication` service with the medication_id

## Example Dashboard

Here's a complete Lovelace dashboard example:

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # 💊 My Medications
  
  - type: entities
    title: Medications
    entities:
      - sensor.aspirin
      - sensor.vitamin_d
  
  - type: grid
    columns: 2
    cards:
      - type: button
        name: Took Aspirin
        icon: mdi:pill
        tap_action:
          action: call-service
          service: pill_assistant.take_medication
          service_data:
            medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"
      
      - type: button
        name: Refill Aspirin
        icon: mdi:package-variant
        tap_action:
          action: call-service
          service: pill_assistant.refill_medication
          service_data:
            medication_id: "{{ state_attr('sensor.aspirin', 'medication_id') }}"
```

## Next Steps

- Explore the [examples/AUTOMATIONS.md](./AUTOMATIONS.md) file for more automation ideas
- Check [examples/configuration.yaml](./configuration.yaml) for helper entities
- Read the main [README.md](../README.md) for complete documentation

## Troubleshooting

### Medication not appearing
- Check Home Assistant logs for errors
- Verify the integration was installed correctly
- Restart Home Assistant

### Notifications not working
- Ensure your notification service is configured
- Replace `notify.mobile_app` with your actual service name
- Test notifications separately first

### Service calls failing
- Verify the medication_id is correct (check sensor attributes)
- Check Home Assistant logs for specific errors
- Ensure the integration is loaded properly

## Support

For issues or questions:
- GitHub Issues: https://github.com/BitBasherr/PillAssistant/issues
- Check Home Assistant logs for detailed error messages
- Review the documentation in the README

Happy medication tracking! 💊
