"""Constants for Pill Assistant integration."""

from __future__ import annotations

from homeassistant.helpers.selector import selector

DOMAIN = "pill_assistant"

# ---------------- Config keys (stored in entry.data) ----------------
CONF_MEDICATION_NAME = "medication_name"
CONF_DOSAGE = "dosage"
CONF_DOSAGE_UNIT = "dosage_unit"
CONF_SCHEDULE_TIMES = "schedule_times"  # List of times in HH:MM format
CONF_SCHEDULE_DAYS = "schedule_days"  # List of days (mon, tue, wed, thu, fri, sat, sun)
CONF_REFILL_AMOUNT = "refill_amount"
CONF_REFILL_REMINDER_DAYS = "refill_reminder_days"
CONF_NOTES = "notes"
CONF_NOTIFY_SERVICES = "notify_services"  # List of notification services to use

# Advanced scheduling
CONF_SCHEDULE_TYPE = (
    "schedule_type"  # "fixed_time", "relative_medication", "relative_sensor"
)
CONF_RELATIVE_TO_MEDICATION = (
    "relative_to_medication"  # Medication ID to schedule relative to
)
CONF_RELATIVE_TO_SENSOR = (
    "relative_to_sensor"  # Sensor entity_id to schedule relative to
)
CONF_RELATIVE_OFFSET_HOURS = "relative_offset_hours"  # Hours offset from reference
CONF_RELATIVE_OFFSET_MINUTES = (
    "relative_offset_minutes"  # Minutes offset from reference
)

# Default values
DEFAULT_DOSAGE_UNIT = "pill(s)"
DEFAULT_REFILL_REMINDER_DAYS = 7
DEFAULT_SCHEDULE_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULT_SCHEDULE_TYPE = "fixed_time"
DEFAULT_RELATIVE_OFFSET_HOURS = 0
DEFAULT_RELATIVE_OFFSET_MINUTES = 0

# Schedule type options
SCHEDULE_TYPE_OPTIONS = [
    {"label": "Fixed Time", "value": "fixed_time"},
    {"label": "After Another Medication", "value": "relative_medication"},
    {"label": "After Sensor Event", "value": "relative_sensor"},
]

# Dosage unit options
DOSAGE_UNIT_OPTIONS = [
    {"label": "Pill(s)", "value": "pill(s)"},
    {"label": "mL", "value": "mL"},
    {"label": "mg", "value": "mg"},
    {"label": "g", "value": "g"},
    {"label": "Tablet(s)", "value": "tablet(s)"},
    {"label": "Capsule(s)", "value": "capsule(s)"},
    {"label": "Drop(s)", "value": "drop(s)"},
    {"label": "Spray(s)", "value": "spray(s)"},
    {"label": "Puff(s)", "value": "puff(s)"},
]

# Days of week options
DAY_OPTIONS = [
    {"label": "Monday", "value": "mon"},
    {"label": "Tuesday", "value": "tue"},
    {"label": "Wednesday", "value": "wed"},
    {"label": "Thursday", "value": "thu"},
    {"label": "Friday", "value": "fri"},
    {"label": "Saturday", "value": "sat"},
    {"label": "Sunday", "value": "sun"},
]

# Selectors
SELECT_DOSAGE_UNIT = selector(
    {"select": {"options": DOSAGE_UNIT_OPTIONS, "mode": "dropdown"}}
)

SELECT_DAYS = selector(
    {"select": {"options": DAY_OPTIONS, "multiple": True, "mode": "list"}}
)

SELECT_TIME = selector({"time": {}})

# Notification service selector
SELECT_NOTIFY_SERVICE = selector(
    {
        "select": {
            "options": [],  # Will be dynamically populated
            "multiple": True,
            "custom_value": True,
            "mode": "dropdown",
        }
    }
)

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.medications"
LOG_FILE_NAME = "pill_assistant_history.log"

# Services
SERVICE_TAKE_MEDICATION = "take_medication"
SERVICE_SKIP_MEDICATION = "skip_medication"
SERVICE_REFILL_MEDICATION = "refill_medication"
SERVICE_TEST_NOTIFICATION = "test_notification"
SERVICE_SNOOZE_MEDICATION = "snooze_medication"

# Attributes
ATTR_MEDICATION_ID = "medication_id"
ATTR_NEXT_DOSE_TIME = "next_dose_time"
ATTR_LAST_TAKEN = "last_taken"
ATTR_DOSES_TODAY = "doses_today"
ATTR_TAKEN_SCHEDULED_RATIO = "taken_scheduled_ratio"
ATTR_REMAINING_AMOUNT = "remaining_amount"
ATTR_SCHEDULE = "schedule"
ATTR_MISSED_DOSES = "missed_doses"
ATTR_SNOOZE_UNTIL = "snooze_until"
ATTR_SNOOZE_DURATION = "snooze_duration"
ATTR_LOG_FILE = "log_file"

# Snooze configuration
CONF_SNOOZE_DURATION_MINUTES = "snooze_duration_minutes"
DEFAULT_SNOOZE_DURATION_MINUTES = 15
