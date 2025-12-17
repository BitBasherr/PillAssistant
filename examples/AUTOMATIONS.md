# Example Automations for Pill Assistant

This directory contains example automations to help you get started with Pill Assistant.

## Basic Notification Examples

### 1. Medication Due Notification
Send a notification when a medication is due to be taken.

```yaml
automation:
  - alias: "Medication Due - MedicationA"
    description: "Send notification when MedicationA is due"
    trigger:
      - platform: state
        entity_id: sensor.medication_a
        to: "due"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "💊 Medication Reminder"
          message: >
            Time to take {{ state_attr('sensor.medication_a', 'dosage') }} 
            {{ state_attr('sensor.medication_a', 'dosage_unit') }} of MedicationA
          data:
            actions:
              - action: "TAKE_MED"
                title: "Mark as Taken"
              - action: "SKIP_MED"
                title: "Skip"
```

### 2. Overdue Medication Alert
Send an alert when a medication dose has been missed.

```yaml
automation:
  - alias: "Medication Overdue - MedicationA"
    description: "Alert when MedicationA dose is overdue"
    trigger:
      - platform: state
        entity_id: sensor.medication_a
        to: "overdue"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⚠️ Missed Dose"
          message: "You have missed your scheduled dose of MedicationA"
          data:
            tag: "overdue_medication_a"
            priority: high
```

### 3. Refill Reminder
Alert when medication supply is running low.

```yaml
automation:
  - alias: "Refill Reminder - MedicationA"
    description: "Remind to refill MedicationA"
    trigger:
      - platform: state
        entity_id: sensor.medication_a
        to: "refill_needed"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.medication_a', 'remaining_amount') | int <= 
             state_attr('sensor.medication_a', 'refill_reminder_days') | int }}
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "📦 Refill Needed"
          message: >
            MedicationA is running low. Only {{ state_attr('sensor.medication_a', 'remaining_amount') }} 
            doses remaining. Please refill soon.
```

## Interactive Button Examples

### 4. Mark Medication as Taken via Button
Use an input button to mark medication as taken.

```yaml
# First, create an input button in configuration.yaml:
input_button:
  took_medication_a:
    name: "Took MedicationA"
    icon: mdi:pill

# Then create the automation:
automation:
  - alias: "Record MedicationA Taken"
    description: "Record when MedicationA button is pressed"
    trigger:
      - platform: state
        entity_id: input_button.took_medication_a
    action:
      - service: pill_assistant.take_medication
        data:
          medication_id: "{{ state_attr('sensor.medication_a', 'medication_id') }}"
      - service: notify.mobile_app_your_phone
        data:
          message: "MedicationA dose recorded at {{ now().strftime('%H:%M') }}"
```

### 5. Quick Action from Notification
Handle notification actions to mark medication as taken or skipped.

```yaml
automation:
  - alias: "Handle Medication Notification Actions"
    description: "Process take/skip actions from notifications"
    trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: "TAKE_MED"
    action:
      - service: pill_assistant.take_medication
        data:
          medication_id: "{{ state_attr('sensor.medication_a', 'medication_id') }}"

  - alias: "Handle Skip Medication Action"
    trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: "SKIP_MED"
    action:
      - service: pill_assistant.skip_medication
        data:
          medication_id: "{{ state_attr('sensor.medication_a', 'medication_id') }}"
```

## Scheduled Reminders

### 6. Daily Medication Summary
Send a summary of all medications due today.

```yaml
automation:
  - alias: "Daily Medication Summary"
    description: "Morning summary of medications"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "📋 Today's Medications"
          message: >
            {% set meds = states.sensor | selectattr('entity_id', 'search', 'sensor\\..*') 
                          | selectattr('attributes.medication_id', 'defined') | list %}
            Today you have {{ meds | count }} medication(s) scheduled:
            {% for med in meds %}
            - {{ med.name }}: {{ state_attr(med.entity_id, 'dosage') }} 
              {{ state_attr(med.entity_id, 'dosage_unit') }}
            {% endfor %}
```

### 7. Voice Announcement via Smart Speaker
Announce medication time through smart speakers.

```yaml
automation:
  - alias: "Medication Voice Reminder"
    description: "Announce medication time"
    trigger:
      - platform: state
        entity_id: sensor.medication_a
        to: "due"
    action:
      - service: tts.google_translate_say
        data:
          entity_id: media_player.living_room_speaker
          message: >
            It's time to take your medication. Please take 
            {{ state_attr('sensor.medication_a', 'dosage') }} 
            {{ state_attr('sensor.medication_a', 'dosage_unit') }} of MedicationA.
```

## Advanced Examples

### 8. Smart Light Indicator
Change light color when medication is due.

```yaml
automation:
  - alias: "Medication Light Indicator"
    description: "Turn light blue when medication is due"
    trigger:
      - platform: state
        entity_id: sensor.medication_a
        to: "due"
    action:
      - service: light.turn_on
        data:
          entity_id: light.bedroom
          color_name: blue
          brightness_pct: 50
      - delay:
          minutes: 30
      - service: light.turn_off
        data:
          entity_id: light.bedroom
```

### 9. Multiple Medication Dashboard Card
Create a Lovelace card to display all medications.

```yaml
# Add to your Lovelace dashboard:
type: entities
title: Medication Tracker
entities:
  - entity: sensor.medication_a
    secondary_info: last-changed
  - entity: sensor.vitamin_d
    secondary_info: last-changed
  - type: section
    label: Actions
  - type: buttons
    entities:
      - entity: input_button.took_medication_a
      - entity: input_button.took_vitamin_d
```

### 10. Medication Adherence Tracking
Track how often medications are taken on time.

```yaml
automation:
  - alias: "Track Medication Adherence"
    description: "Log adherence to medication schedule"
    trigger:
      - platform: state
        entity_id: sensor.medication_a
        to: "taken"
    action:
      - service: logbook.log
        data:
          name: "Medication Adherence"
          message: >
            MedicationA taken at {{ now().strftime('%H:%M') }}. 
            Remaining: {{ state_attr('sensor.medication_a', 'remaining_amount') }}
          entity_id: sensor.medication_a
```

### 11. Auto-Refill Reminder Based on Pharmacy Schedule
Remind to refill on specific days before running out.

```yaml
automation:
  - alias: "Pharmacy Refill Day Reminder"
    description: "Remind to call pharmacy for refill"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: state
        entity_id: sensor.medication_a
        state: "refill_needed"
      - condition: time
        weekday:
          - mon
          - wed
          - fri
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "📞 Call Pharmacy"
          message: "Don't forget to call the pharmacy to refill your MedicationA prescription"
```

### 12. Medication History Report
Generate a weekly report of medication history.

```yaml
automation:
  - alias: "Weekly Medication Report"
    description: "Send weekly adherence report"
    trigger:
      - platform: time
        at: "20:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "📊 Weekly Medication Report"
          message: >
            Check your pill_assistant_history.log file for detailed 
            medication history from the past week.
```

## Tips

1. **Get Medication ID**: Use `{{ state_attr('sensor.your_medication', 'medication_id') }}` to get the medication ID for service calls.

2. **Multiple Medications**: Create separate automations for each medication or use templates to handle multiple medications in one automation.

3. **Persistent Notifications**: Use `persistent_notification` service for important reminders that stay visible.

4. **Location-Based**: Add location conditions to only send reminders when you're at home.

5. **Time Windows**: Use time conditions to avoid notifications during sleep hours.

## Lovelace Dashboard Example

```yaml
views:
  - title: Medications
    icon: mdi:pill
    cards:
      - type: vertical-stack
        cards:
          - type: markdown
            content: |
              # 💊 Medication Tracker
              Track and manage your daily medications
          
          - type: entities
            title: Active Medications
            show_header_toggle: false
            entities:
              - entity: sensor.medication_a
                secondary_info: last-changed
                icon: mdi:pill
              - entity: sensor.vitamin_d
                secondary_info: last-changed
                icon: mdi:vitamin
          
          - type: glance
            title: Quick Status
            entities:
              - entity: sensor.medication_a
                name: MedicationA
              - entity: sensor.vitamin_d
                name: Vitamin D
          
          - type: button
            name: Mark MedicationA Taken
            tap_action:
              action: call-service
              service: pill_assistant.take_medication
              service_data:
                medication_id: "{{ state_attr('sensor.medication_a', 'medication_id') }}"
          
          - type: history-graph
            title: Medication History (24h)
            hours_to_show: 24
            entities:
              - sensor.medication_a
              - sensor.vitamin_d
```

## More Information

- See the main README.md for complete documentation
- Check the Home Assistant logs for detailed medication tracking information
- Review `pill_assistant_history.log` for persistent medication history
