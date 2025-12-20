"""Constants for Pill Assistant integration."""

from __future__ import annotations

from homeassistant.helpers.selector import selector

DOMAIN = "pill_assistant"

# ---------------- Config keys (stored in entry.data) ----------------
CONF_MEDICATION_NAME = "medication_name"
CONF_DOSAGE = "dosage"
CONF_DOSAGE_UNIT = "dosage_unit"
CONF_MEDICATION_TYPE = (
    "medication_type"  # Type of medication (pill, tablet, liquid, etc.)
)
CONF_SCHEDULE_TIMES = "schedule_times"  # List of times in HH:MM format
CONF_SCHEDULE_DAYS = "schedule_days"  # List of days (mon, tue, wed, thu, fri, sat, sun)
CONF_REFILL_AMOUNT = "refill_amount"
CONF_REFILL_REMINDER_DAYS = "refill_reminder_days"
CONF_CURRENT_QUANTITY = "current_quantity"  # Current/starting quantity
CONF_USE_CUSTOM_QUANTITY = (
    "use_custom_quantity"  # Use custom starting quantity instead of refill amount
)
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
CONF_SENSOR_TRIGGER_VALUE = (
    "sensor_trigger_value"  # Specific sensor value to trigger on
)
CONF_SENSOR_TRIGGER_ATTRIBUTE = (
    "sensor_trigger_attribute"  # Specific sensor attribute to monitor (optional)
)
CONF_AVOID_DUPLICATE_TRIGGERS = (
    "avoid_duplicate_triggers"  # Avoid triggering multiple times for same sensor event
)
CONF_IGNORE_UNAVAILABLE = "ignore_unavailable"  # Ignore 'unknown' and 'unavailable' states when monitoring for changes
CONF_ENABLE_AUTOMATIC_NOTIFICATIONS = "enable_automatic_notifications"  # Enable automatic notifications at scheduled times
CONF_ON_TIME_WINDOW_MINUTES = (
    "on_time_window_minutes"  # Time window (±minutes) for "on time" statistics
)

# Default values
DEFAULT_DOSAGE_UNIT = "each"
DEFAULT_MEDICATION_TYPE = "pill"
DEFAULT_REFILL_REMINDER_DAYS = 7
DEFAULT_SCHEDULE_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULT_SCHEDULE_TYPE = "fixed_time"
DEFAULT_RELATIVE_OFFSET_HOURS = 0
DEFAULT_RELATIVE_OFFSET_MINUTES = 0
DEFAULT_SENSOR_TRIGGER_VALUE = ""
DEFAULT_SENSOR_TRIGGER_ATTRIBUTE = ""
DEFAULT_AVOID_DUPLICATE_TRIGGERS = True
DEFAULT_IGNORE_UNAVAILABLE = True
DEFAULT_ENABLE_AUTOMATIC_NOTIFICATIONS = True
DEFAULT_ON_TIME_WINDOW_MINUTES = 30

# Schedule type options
SCHEDULE_TYPE_OPTIONS = [
    {"label": "Fixed Time", "value": "fixed_time"},
    {"label": "After Another Medication", "value": "relative_medication"},
    {"label": "After Sensor Event", "value": "relative_sensor"},
]

# Medication type options (form of medication)
MEDICATION_TYPE_OPTIONS = [
    {"label": "Pill", "value": "pill"},
    {"label": "Tablet", "value": "tablet"},
    {"label": "Capsule", "value": "capsule"},
    {"label": "Gelatin Capsule", "value": "gelatin_capsule"},
    {"label": "Gummy", "value": "gummy"},
    {"label": "Liquid", "value": "liquid"},
    {"label": "Syrup", "value": "syrup"},
    {"label": "Drop", "value": "drop"},
    {"label": "Spray", "value": "spray"},
    {"label": "Puff", "value": "puff"},
    {"label": "Injection", "value": "injection"},
    {"label": "Patch", "value": "patch"},
    {"label": "Cream/Ointment", "value": "cream"},
    {"label": "Powder", "value": "powder"},
    {"label": "Other", "value": "other"},
]

# Dosage unit options (measurement units)
DOSAGE_UNIT_OPTIONS = [
    {"label": "Each", "value": "each"},
    {"label": "mL", "value": "mL"},
    {"label": "mg", "value": "mg"},
    {"label": "g", "value": "g"},
    {"label": "mcg", "value": "mcg"},
    {"label": "tsp", "value": "tsp"},
    {"label": "TBSP", "value": "TBSP"},
    {"label": "units", "value": "units"},
    {"label": "IU", "value": "IU"},
]

# Legacy dosage units that combined type and unit (for migration)
LEGACY_DOSAGE_UNITS = {
    "pill(s)": ("pill", "each"),
    "tablet(s)": ("tablet", "each"),
    "capsule(s)": ("capsule", "each"),
    "gelatin_capsule(s)": ("gelatin_capsule", "each"),
    "gummy/gummies": ("gummy", "each"),
    "drop(s)": ("drop", "each"),
    "spray(s)": ("spray", "each"),
    "puff(s)": ("puff", "each"),
    "syrup_mL": ("syrup", "mL"),
}

# Specific measurement units that should be preferred over generic types
SPECIFIC_DOSAGE_UNITS = ["mL", "mg", "g", "mcg", "tsp", "TBSP", "each", "units", "IU"]

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
SELECT_MEDICATION_TYPE = selector(
    {"select": {"options": MEDICATION_TYPE_OPTIONS, "mode": "dropdown"}}
)

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
SERVICE_INCREMENT_DOSAGE = "increment_dosage"
SERVICE_DECREMENT_DOSAGE = "decrement_dosage"
SERVICE_INCREMENT_REMAINING = "increment_remaining"
SERVICE_DECREMENT_REMAINING = "decrement_remaining"
SERVICE_GET_STATISTICS = "get_statistics"
SERVICE_GET_MEDICATION_HISTORY = "get_medication_history"
SERVICE_EDIT_MEDICATION_HISTORY = "edit_medication_history"
SERVICE_DELETE_MEDICATION_HISTORY = "delete_medication_history"

# Service parameter keys (for service calls)
ATTR_MEDICATION_ID = "medication_id"
ATTR_SNOOZE_DURATION = "snooze_duration"
ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"
ATTR_HISTORY_INDEX = "history_index"
ATTR_TIMESTAMP = "timestamp"
ATTR_ACTION = "action"
ATTR_DOSAGE = "dosage"
ATTR_DOSAGE_UNIT = "dosage_unit"
ATTR_AMOUNT = "amount"

# Display attribute names (for entity state attributes - human-friendly)
ATTR_DISPLAY_MEDICATION_ID = "Medication ID"
ATTR_NEXT_DOSE_TIME = "Next dose time"
ATTR_LAST_TAKEN = "Last taken at"
ATTR_REMAINING_AMOUNT = "Remaining amount"
ATTR_SCHEDULE = "Schedule"
ATTR_MISSED_DOSES = "Missed doses"
ATTR_SNOOZE_UNTIL = "Snooze until"
ATTR_DOSES_TAKEN_TODAY = "Doses taken today"
ATTR_TAKEN_SCHEDULED_RATIO = "Taken/Scheduled ratio"
ATTR_LOG_FILE_LOCATION = "Log file location"

# Snooze configuration
CONF_SNOOZE_DURATION_MINUTES = "snooze_duration_minutes"
DEFAULT_SNOOZE_DURATION_MINUTES = 15

# Sensor event history configuration
MAX_SENSOR_HISTORY_CHANGES = 20  # Maximum number of state changes to display
