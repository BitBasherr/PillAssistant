"""Sensor platform for Pill Assistant."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN,
    LOG_FILE_NAME,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_MEDICATION_TYPE,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TYPE,
    CONF_RELATIVE_TO_MEDICATION,
    CONF_RELATIVE_TO_SENSOR,
    CONF_RELATIVE_OFFSET_HOURS,
    CONF_RELATIVE_OFFSET_MINUTES,
    CONF_SENSOR_TRIGGER_VALUE,
    CONF_SENSOR_TRIGGER_ATTRIBUTE,
    CONF_AVOID_DUPLICATE_TRIGGERS,
    CONF_IGNORE_UNAVAILABLE,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    CONF_NOTES,
    CONF_NOTIFY_SERVICES,
    CONF_ENABLE_AUTOMATIC_NOTIFICATIONS,
    CONF_ON_TIME_WINDOW_MINUTES,
    DEFAULT_SCHEDULE_TYPE,
    DEFAULT_DOSAGE_UNIT,
    DEFAULT_MEDICATION_TYPE,
    DEFAULT_SENSOR_TRIGGER_VALUE,
    DEFAULT_SENSOR_TRIGGER_ATTRIBUTE,
    DEFAULT_AVOID_DUPLICATE_TRIGGERS,
    DEFAULT_IGNORE_UNAVAILABLE,
    DEFAULT_ENABLE_AUTOMATIC_NOTIFICATIONS,
    DEFAULT_ON_TIME_WINDOW_MINUTES,
    SPECIFIC_DOSAGE_UNITS,
    ATTR_DISPLAY_MEDICATION_ID,
    ATTR_NEXT_DOSE_TIME,
    ATTR_LAST_TAKEN,
    ATTR_REMAINING_AMOUNT,
    ATTR_SCHEDULE,
    ATTR_MISSED_DOSES,
    ATTR_SNOOZE_UNTIL,
    ATTR_DOSES_TAKEN_TODAY,
    ATTR_TAKEN_SCHEDULED_RATIO,
    ATTR_LOG_FILE_LOCATION,
)
from . import log_utils

_LOGGER = logging.getLogger(__name__)


def normalize_dosage_unit(dosage_unit: str | None) -> str:
    """
    Normalize dosage unit for backward compatibility.

    If a specific unit (mg, mL, g, tsp, TBSP, each) is found, use it.
    Otherwise, default to the provided unit or DEFAULT_DOSAGE_UNIT.
    """
    if not dosage_unit:
        return DEFAULT_DOSAGE_UNIT

    # Check if it's already a specific unit (exact match)
    if dosage_unit in SPECIFIC_DOSAGE_UNITS:
        return dosage_unit

    # Check if a specific unit is embedded in the string (e.g., "500mg", "10mL")
    # Use word boundaries or numeric prefixes to avoid false matches
    # Try to find the longest matching specific unit
    dosage_unit_lower = dosage_unit.lower()
    longest_match = None
    longest_match_len = 0

    for specific_unit in SPECIFIC_DOSAGE_UNITS:
        specific_lower = specific_unit.lower()
        # Check if the unit appears at word boundaries or after digits
        if specific_lower in dosage_unit_lower:
            idx = dosage_unit_lower.find(specific_lower)
            if idx >= 0:
                # Check if it's preceded by a digit or at the start
                # and followed by nothing or non-letter
                before_ok = (
                    idx == 0
                    or dosage_unit_lower[idx - 1].isdigit()
                    or not dosage_unit_lower[idx - 1].isalpha()
                )
                after_idx = idx + len(specific_lower)
                after_ok = (
                    after_idx >= len(dosage_unit_lower)
                    or not dosage_unit_lower[after_idx].isalpha()
                )

                if before_ok and after_ok and len(specific_lower) > longest_match_len:
                    longest_match = specific_unit
                    longest_match_len = len(specific_lower)

    if longest_match:
        return longest_match

    # Return as-is if it's already in the system, otherwise default to pill(s)
    return dosage_unit if dosage_unit else DEFAULT_DOSAGE_UNIT


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Pill Assistant sensor."""
    async_add_entities([PillAssistantSensor(hass, entry)], True)


class PillAssistantSensor(SensorEntity):
    """Representation of a Pill Assistant medication sensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._medication_name = entry.data.get(
            CONF_MEDICATION_NAME, "Unknown Medication"
        )
        self._attr_name = f"PA_{self._medication_name.title()}"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_native_value = "scheduled"
        self._medication_id = entry.entry_id
        self._last_notification_time = None  # Track when we last sent a notification

        # Get storage data
        self._store_data = hass.data[DOMAIN][entry.entry_id]

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Subscribe to dispatcher signal for immediate updates
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"pill_assistant_medication_updated_{self._medication_id}",
                self._async_update,
            )
        )

        # Update every minute to check for missed doses
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_update,
                timedelta(minutes=1),
            )
        )
        await self._async_update(None)

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        if self._attr_native_value == "due":
            return "mdi:pill"
        elif self._attr_native_value == "taken":
            return "mdi:check-circle"
        elif self._attr_native_value == "overdue":
            return "mdi:alert-circle"
        elif self._attr_native_value == "refill_needed":
            return "mdi:package-variant"
        return "mdi:calendar-clock"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._medication_id)},
            name=f"Pill Assistant - {self._medication_name}",
            manufacturer="Pill Assistant",
            model="Medication Tracker",
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        storage_data = self._store_data["storage_data"]
        med_data = storage_data["medications"].get(self._medication_id, {})

        schedule_times = self._entry.data.get(CONF_SCHEDULE_TIMES, [])
        schedule_days = self._entry.data.get(CONF_SCHEDULE_DAYS, [])
        schedule_type = self._entry.data.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE)

        # Format schedule as human-readable string
        schedule_str = self._format_schedule_string(
            schedule_type, schedule_times, schedule_days
        )

        # Calculate doses taken today and taken/scheduled ratio
        doses_today = self._get_doses_taken_today()
        scheduled_today = self._get_scheduled_doses_today()
        ratio_str = f"{len(doses_today)}/{scheduled_today}"

        # Get log file paths - both global and per-medication
        global_log_path = log_utils.get_global_log_path(self.hass)
        med_log_path = log_utils.get_medication_log_path(
            self.hass, self._medication_name
        )

        # Use med_data for dosage so increment/decrement reflects in UI
        dosage = med_data.get(CONF_DOSAGE, self._entry.data.get(CONF_DOSAGE, ""))
        dosage_unit = normalize_dosage_unit(
            med_data.get(CONF_DOSAGE_UNIT, self._entry.data.get(CONF_DOSAGE_UNIT, ""))
        )
        medication_type = med_data.get(
            CONF_MEDICATION_TYPE,
            self._entry.data.get(CONF_MEDICATION_TYPE, DEFAULT_MEDICATION_TYPE),
        )

        # Format dosage display with type and unit
        # Make pluralization dynamic based on dosage amount
        try:
            dosage_num = float(dosage)
            # Pluralize medication type if dosage > 1
            if dosage_num == 1:
                type_display = medication_type
            else:
                # Handle special plurals
                if medication_type.endswith("y"):
                    type_display = (
                        medication_type[:-1] + "ies"
                    )  # e.g., gummy -> gummies
                elif medication_type in ["patch", "each"]:
                    type_display = medication_type + "es"
                else:
                    type_display = medication_type + "s"
        except (ValueError, TypeError):
            # If dosage is not a number, keep medication type as-is
            type_display = medication_type

        dosage_display = f"{dosage} {type_display} ({dosage_unit})"

        # Use human-friendly keys as per requirements but keep backward compatibility
        attributes = {
            # Human-friendly attribute names
            ATTR_DISPLAY_MEDICATION_ID: self._medication_id,
            "Dosage": dosage_display,
            "Medication Type": medication_type,
            ATTR_SCHEDULE: schedule_str,
            ATTR_REMAINING_AMOUNT: med_data.get("remaining_amount", 0),
            ATTR_LAST_TAKEN: med_data.get("last_taken") or "Never",
            "Refill amount": self._entry.data.get(CONF_REFILL_AMOUNT, 0),
            "Refill reminder days": self._entry.data.get(CONF_REFILL_REMINDER_DAYS, 0),
            ATTR_DOSES_TAKEN_TODAY: doses_today,
            ATTR_TAKEN_SCHEDULED_RATIO: ratio_str,
            "Global log path": global_log_path,
            "Medication log path": med_log_path,
            "Automatic notifications enabled": self._entry.data.get(
                CONF_ENABLE_AUTOMATIC_NOTIFICATIONS,
                DEFAULT_ENABLE_AUTOMATIC_NOTIFICATIONS,
            ),
            "On-time window (minutes)": self._entry.data.get(
                CONF_ON_TIME_WINDOW_MINUTES, DEFAULT_ON_TIME_WINDOW_MINUTES
            ),
            # Keep backward-compatible keys for existing automations
            "remaining_amount": med_data.get("remaining_amount", 0),
            "last_taken": med_data.get("last_taken"),
            "dosage": dosage,
            "dosage_unit": dosage_unit,
            "medication_type": medication_type,
            "log_file_location": global_log_path,  # Backward compatibility
        }

        # Add notes if present
        notes = self._entry.data.get(CONF_NOTES, "")
        if notes:
            attributes["Notes"] = notes
            attributes["notes"] = notes

        # Add snooze information if snoozed
        snooze_until_str = med_data.get("snooze_until")
        if snooze_until_str:
            attributes[ATTR_SNOOZE_UNTIL] = snooze_until_str
            attributes["snooze_until"] = snooze_until_str

        # Calculate next dose time
        next_dose = self._calculate_next_dose()
        if next_dose:
            attributes[ATTR_NEXT_DOSE_TIME] = next_dose.isoformat()
            attributes["next_dose_time"] = next_dose.isoformat()

        # Get missed doses
        missed_doses = self._get_missed_doses()
        if missed_doses:
            attributes[ATTR_MISSED_DOSES] = missed_doses
            attributes["missed_doses"] = missed_doses

        return attributes

    def _format_schedule_string(
        self, schedule_type: str, schedule_times: list, schedule_days: list
    ) -> str:
        """Format schedule as human-readable string."""
        if schedule_type == "fixed_time":
            times_str = ", ".join(schedule_times) if schedule_times else "No times"
            days_str = ", ".join(schedule_days) if schedule_days else "No days"
            return f"{times_str} on {days_str}"
        elif schedule_type == "relative_medication":
            rel_med_id = self._entry.data.get(CONF_RELATIVE_TO_MEDICATION)
            offset_hours = self._entry.data.get(CONF_RELATIVE_OFFSET_HOURS, 0)
            offset_minutes = self._entry.data.get(CONF_RELATIVE_OFFSET_MINUTES, 0)
            rel_med_name = "unknown medication"
            if rel_med_id and rel_med_id in self.hass.data.get(DOMAIN, {}):
                ref_entry_data = self.hass.data[DOMAIN][rel_med_id]
                ref_entry = ref_entry_data.get("entry")
                if ref_entry:
                    rel_med_name = ref_entry.data.get(CONF_MEDICATION_NAME, "unknown")
            offset_str = self._format_time_offset(offset_hours, offset_minutes)
            return f"{offset_str} after {rel_med_name}"
        elif schedule_type == "relative_sensor":
            sensor_id = self._entry.data.get(CONF_RELATIVE_TO_SENSOR, "unknown sensor")
            offset_hours = self._entry.data.get(CONF_RELATIVE_OFFSET_HOURS, 0)
            offset_minutes = self._entry.data.get(CONF_RELATIVE_OFFSET_MINUTES, 0)
            offset_str = self._format_time_offset(offset_hours, offset_minutes)
            return f"{offset_str} after {sensor_id}"
        return "Unknown schedule type"

    def _format_time_offset(self, hours: int, minutes: int) -> str:
        """Format a time offset as a human-readable string."""
        # Ensure non-negative values
        hours = abs(hours) if hours else 0
        minutes = abs(minutes) if minutes else 0

        parts = []
        if hours > 0:
            parts.append(f"{hours} hr" if hours == 1 else f"{hours} hrs")
        if minutes > 0:
            parts.append(f"{minutes} min")
        if not parts:
            return "0 min"
        return " ".join(parts)

    def _get_doses_taken_today(self) -> list:
        """Get list of dose timestamps taken today."""
        storage_data = self._store_data["storage_data"]
        history = storage_data.get("history", [])

        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        doses_today = []
        for entry in history:
            if (
                entry.get("medication_id") == self._medication_id
                and entry.get("action") == "taken"
            ):
                try:
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    if timestamp >= today_start:
                        doses_today.append(timestamp.strftime("%H:%M"))
                except (ValueError, KeyError):
                    continue

        return doses_today

    def _get_scheduled_doses_today(self) -> int:
        """Get count of scheduled doses for today."""
        schedule_type = self._entry.data.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE)
        schedule_times = self._entry.data.get(CONF_SCHEDULE_TIMES, [])
        schedule_days = self._entry.data.get(CONF_SCHEDULE_DAYS, [])

        now = dt_util.now()
        today_day = now.strftime("%a").lower()[:3]

        # Check if today is a scheduled day
        if today_day not in schedule_days:
            return 0

        # For fixed time schedule, return number of scheduled times
        if schedule_type == "fixed_time":
            return len(schedule_times)

        # For relative schedules, return 1 (assuming one dose per day)
        return 1

    def _calculate_next_dose(self) -> datetime | None:
        """Calculate the next dose time based on schedule type."""
        schedule_type = self._entry.data.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE)
        schedule_days = self._entry.data.get(CONF_SCHEDULE_DAYS, [])

        # Map full day names to 3-letter abbreviations
        day_map = {
            "monday": "mon",
            "tuesday": "tue",
            "wednesday": "wed",
            "thursday": "thu",
            "friday": "fri",
            "saturday": "sat",
            "sunday": "sun",
        }

        # Normalize schedule_days
        normalized_days = []
        for day in schedule_days:
            day_lower = day.lower()
            if day_lower in day_map.values():
                normalized_days.append(day_lower)
            elif day_lower in day_map:
                normalized_days.append(day_map[day_lower])

        if schedule_type == "fixed_time":
            return self._calculate_fixed_time_dose(normalized_days)
        elif schedule_type == "relative_medication":
            return self._calculate_relative_medication_dose(normalized_days)
        elif schedule_type == "relative_sensor":
            return self._calculate_relative_sensor_dose(normalized_days)

        return None

    def _calculate_fixed_time_dose(self, normalized_days: list) -> datetime | None:
        """Calculate next dose for fixed time schedule."""
        schedule_times = self._entry.data.get(CONF_SCHEDULE_TIMES, [])

        if not schedule_times or not normalized_days:
            return None

        now = dt_util.now()

        # Find next scheduled time
        for day_offset in range(8):  # Check next 7 days plus today
            check_date = now + timedelta(days=day_offset)
            check_day = check_date.strftime("%a").lower()[:3]

            if check_day not in normalized_days:
                continue

            for time_str in schedule_times:
                try:
                    # Handle both single time and list of times
                    if isinstance(time_str, list):
                        time_str = time_str[0] if time_str else "00:00"

                    hour, minute = map(int, time_str.split(":"))
                    dose_time = check_date.replace(
                        hour=hour, minute=minute, second=0, microsecond=0
                    )

                    # Only return future times
                    if dose_time > now:
                        return dose_time
                except (ValueError, AttributeError) as e:
                    _LOGGER.error("Error parsing time %s: %s", time_str, e)
                    continue

        return None

    def _calculate_relative_medication_dose(
        self, normalized_days: list
    ) -> datetime | None:
        """Calculate next dose relative to another medication."""
        rel_med_id = self._entry.data.get(CONF_RELATIVE_TO_MEDICATION)
        offset_hours = self._entry.data.get(CONF_RELATIVE_OFFSET_HOURS, 0)
        offset_minutes = self._entry.data.get(CONF_RELATIVE_OFFSET_MINUTES, 0)

        if not rel_med_id:
            return None

        # Get the reference medication's last taken time
        if rel_med_id not in self.hass.data[DOMAIN]:
            return None

        ref_entry_data = self.hass.data[DOMAIN][rel_med_id]
        ref_storage_data = ref_entry_data["storage_data"]
        ref_med_data = ref_storage_data["medications"].get(rel_med_id, {})
        ref_last_taken_str = ref_med_data.get("last_taken")

        if not ref_last_taken_str:
            # If reference medication hasn't been taken yet, return None
            return None

        try:
            ref_last_taken = datetime.fromisoformat(ref_last_taken_str)
        except (ValueError, TypeError):
            return None

        # Calculate next dose time as offset from reference medication
        next_dose = ref_last_taken + timedelta(
            hours=offset_hours, minutes=offset_minutes
        )

        # Check if it's on a valid day
        now = dt_util.now()
        check_day = next_dose.strftime("%a").lower()[:3]

        if check_day not in normalized_days:
            # Find next valid day
            for day_offset in range(1, 8):
                check_date = next_dose + timedelta(days=day_offset)
                check_day = check_date.strftime("%a").lower()[:3]
                if check_day in normalized_days:
                    next_dose = check_date
                    break

        # Only return if in the future
        if next_dose > now:
            return next_dose

        return None

    def _calculate_relative_sensor_dose(self, normalized_days: list) -> datetime | None:
        """Calculate next dose relative to a sensor event."""
        sensor_entity_id = self._entry.data.get(CONF_RELATIVE_TO_SENSOR)
        offset_hours = self._entry.data.get(CONF_RELATIVE_OFFSET_HOURS, 0)
        offset_minutes = self._entry.data.get(CONF_RELATIVE_OFFSET_MINUTES, 0)
        trigger_value = self._entry.data.get(
            CONF_SENSOR_TRIGGER_VALUE, DEFAULT_SENSOR_TRIGGER_VALUE
        )
        trigger_attribute = self._entry.data.get(
            CONF_SENSOR_TRIGGER_ATTRIBUTE, DEFAULT_SENSOR_TRIGGER_ATTRIBUTE
        )
        avoid_duplicates = self._entry.data.get(
            CONF_AVOID_DUPLICATE_TRIGGERS, DEFAULT_AVOID_DUPLICATE_TRIGGERS
        )
        ignore_unavailable = self._entry.data.get(
            CONF_IGNORE_UNAVAILABLE, DEFAULT_IGNORE_UNAVAILABLE
        )

        if not sensor_entity_id:
            return None

        # Get the sensor's last changed time
        sensor_state = self.hass.states.get(sensor_entity_id)
        if not sensor_state:
            return None

        sensor_last_changed = sensor_state.last_changed
        if not sensor_last_changed:
            return None

        # Get the value to check (either state or attribute)
        if trigger_attribute:
            # Check attribute value
            current_value = sensor_state.attributes.get(trigger_attribute)
            if current_value is None:
                return None
            # Safely convert to string, handling complex objects
            try:
                current_value = str(current_value).lower()
            except (TypeError, AttributeError):
                # If conversion fails, skip this trigger
                return None
        else:
            # Check state value
            try:
                current_value = (
                    str(sensor_state.state).lower() if sensor_state.state else ""
                )
            except (TypeError, AttributeError):
                # If conversion fails, skip this trigger
                return None

        # Ignore unavailable/unknown states if configured
        if ignore_unavailable and current_value in [
            "unknown",
            "unavailable",
            "none",
            "",
        ]:
            return None

        # Check if trigger value matches (if specified)
        if trigger_value:
            trigger_value_lower = trigger_value.lower()

            # Only trigger if the current value matches the trigger value
            if current_value != trigger_value_lower:
                return None

        # If avoiding duplicates, check if we've already triggered for this sensor event
        if avoid_duplicates:
            storage_data = self._store_data["storage_data"]
            last_sensor_trigger = storage_data.get("last_sensor_trigger", {}).get(
                self._entry.entry_id
            )

            # If we've already triggered for this exact sensor change time, skip
            if (
                last_sensor_trigger
                and last_sensor_trigger == sensor_last_changed.isoformat()
            ):
                return None

        # Calculate next dose time as offset from sensor event
        next_dose = sensor_last_changed + timedelta(
            hours=offset_hours, minutes=offset_minutes
        )

        # Check if it's on a valid day
        now = dt_util.now()
        check_day = next_dose.strftime("%a").lower()[:3]

        if check_day not in normalized_days:
            # Find next valid day
            for day_offset in range(1, 8):
                check_date = next_dose + timedelta(days=day_offset)
                check_day = check_date.strftime("%a").lower()[:3]
                if check_day in normalized_days:
                    next_dose = check_date
                    break

        # Only return if in the future
        if next_dose > now:
            return next_dose

        return None

    def _get_missed_doses(self) -> list:
        """Get list of missed doses."""
        schedule_times = self._entry.data.get(CONF_SCHEDULE_TIMES, [])
        schedule_days = self._entry.data.get(CONF_SCHEDULE_DAYS, [])

        if not schedule_times or not schedule_days:
            return []

        now = dt_util.now()
        storage_data = self._store_data["storage_data"]
        med_data = storage_data["medications"].get(self._medication_id, {})
        last_taken_str = med_data.get("last_taken")

        last_taken = None
        if last_taken_str:
            try:
                last_taken = datetime.fromisoformat(last_taken_str)
            except (ValueError, TypeError):
                pass

        # Collect all scheduled dose times in the last 24 hours (use a set to avoid duplicates)
        scheduled_dose_times = set()

        # Check each day in the last 2 days to cover 24 hour window
        for day_offset in range(2):
            check_date = now - timedelta(days=day_offset)
            check_day = check_date.strftime("%a").lower()[:3]

            if check_day not in schedule_days:
                continue

            for time_str in schedule_times:
                try:
                    if isinstance(time_str, list):
                        time_str = time_str[0] if time_str else "00:00"

                    hour, minute = map(int, time_str.split(":"))
                    dose_time = check_date.replace(
                        hour=hour, minute=minute, second=0, microsecond=0
                    )

                    # Only consider doses within last 24 hours
                    time_diff = (now - dose_time).total_seconds()
                    if 0 < time_diff <= 86400:  # Between 0 and 24 hours ago
                        scheduled_dose_times.add(dose_time)
                except (ValueError, AttributeError):
                    continue

        # Filter for actually missed doses
        missed = []
        for dose_time in sorted(scheduled_dose_times):
            # If dose time is in the past and after last taken
            if dose_time < now:
                if last_taken is None or dose_time > last_taken:
                    # Check if it's more than 30 minutes overdue
                    if (now - dose_time).total_seconds() > 1800:
                        missed.append(dose_time.isoformat())

        return missed[:5]  # Limit to 5 most recent

    async def _send_automatic_notification(self) -> None:
        """Send automatic notification when medication is due."""
        # Check if automatic notifications are enabled
        enable_auto_notify = self._entry.data.get(
            CONF_ENABLE_AUTOMATIC_NOTIFICATIONS, DEFAULT_ENABLE_AUTOMATIC_NOTIFICATIONS
        )
        if not enable_auto_notify:
            return

        # Get notification services
        notify_services = self._entry.data.get(CONF_NOTIFY_SERVICES, [])
        if not notify_services:
            return

        # Check if we already sent a notification recently (within the last hour)
        now = dt_util.now()
        if self._last_notification_time:
            try:
                last_notif = datetime.fromisoformat(self._last_notification_time)
                # Don't send another notification if we sent one within the last hour
                if (now - last_notif).total_seconds() < 3600:
                    return
            except (ValueError, TypeError):
                pass

        # Get medication details from storage
        storage_data = self._store_data["storage_data"]
        med_data = storage_data["medications"].get(self._medication_id, {})

        med_name = med_data.get(CONF_MEDICATION_NAME, self._medication_name)
        dosage = med_data.get(CONF_DOSAGE, self._entry.data.get(CONF_DOSAGE, ""))
        dosage_unit = med_data.get(
            CONF_DOSAGE_UNIT, self._entry.data.get(CONF_DOSAGE_UNIT, "")
        )
        medication_type = med_data.get(
            CONF_MEDICATION_TYPE,
            self._entry.data.get(CONF_MEDICATION_TYPE, DEFAULT_MEDICATION_TYPE),
        )

        # Create notification message with type
        message = (
            f"Time to take {dosage} {medication_type}(s) of {med_name} ({dosage_unit})"
        )
        title = "Medication Reminder"

        # Send notification to configured services
        for service_name in notify_services:
            try:
                # Extract domain and service
                service_parts = service_name.split(".")
                if len(service_parts) == 2:
                    domain, service = service_parts
                    await self.hass.services.async_call(
                        domain,
                        service,
                        {
                            "title": title,
                            "message": message,
                            "data": {
                                "tag": f"pill_assistant_{self._medication_id}",
                                "actions": [
                                    {
                                        "action": f"take_medication_{self._medication_id}",
                                        "title": "Mark as Taken",
                                    },
                                    {
                                        "action": f"snooze_medication_{self._medication_id}",
                                        "title": "Snooze",
                                    },
                                    {
                                        "action": f"skip_medication_{self._medication_id}",
                                        "title": "Skip",
                                    },
                                ],
                            },
                        },
                        blocking=False,
                    )
            except Exception as err:  # pragma: no cover - notify failure
                _LOGGER.error(
                    "Failed to send automatic notification via %s: %s",
                    service_name,
                    err,
                )

        # Update last notification time
        self._last_notification_time = now.isoformat()
        _LOGGER.info("Automatic notification sent for %s", med_name)

    @callback
    async def _async_update(self, _now=None) -> None:
        """Update the sensor state."""
        storage_data = self._store_data["storage_data"]
        med_data = storage_data["medications"].get(self._medication_id, {})

        remaining = med_data.get("remaining_amount", 0)
        refill_reminder_days = self._entry.data.get(CONF_REFILL_REMINDER_DAYS, 7)

        # Check if medication is snoozed
        now = dt_util.now()
        snooze_until_str = med_data.get("snooze_until")
        is_snoozed = False

        if snooze_until_str:
            try:
                snooze_until = datetime.fromisoformat(snooze_until_str)
                if snooze_until > now:
                    is_snoozed = True
                else:
                    # Snooze period has expired, clear it
                    store = self._store_data["store"]
                    
                    def clear_snooze(data: dict) -> None:
                        """Clear snooze atomically."""
                        med_data = data["medications"].get(self._medication_id)
                        if med_data:
                            med_data["snooze_until"] = None
                    
                    await store.async_update(clear_snooze)
            except (ValueError, TypeError):
                pass

        # Calculate if refill is needed
        # Assuming one dose per scheduled time
        schedule_times = self._entry.data.get(CONF_SCHEDULE_TIMES, [])
        schedule_days = self._entry.data.get(CONF_SCHEDULE_DAYS, [])
        doses_per_week = len(schedule_times) * len(schedule_days)
        doses_per_day = doses_per_week / 7 if schedule_days else 0
        days_remaining = remaining / doses_per_day if doses_per_day > 0 else 0

        if days_remaining <= refill_reminder_days:
            self._attr_native_value = "refill_needed"
        else:
            # Check if dose is due (but respect snooze)
            next_dose = self._calculate_next_dose()

            if next_dose:
                time_to_dose = (next_dose - now).total_seconds()

                # If snoozed, don't mark as due or overdue
                if is_snoozed:
                    self._attr_native_value = "scheduled"
                # Due if within 30 minutes
                elif 0 <= time_to_dose <= 1800:
                    # Set state to due
                    previous_state = self._attr_native_value
                    self._attr_native_value = "due"
                    # Send automatic notification if state changed to due
                    if previous_state != "due":
                        await self._send_automatic_notification()
                # Overdue if missed by more than 30 minutes
                elif time_to_dose < 0:
                    self._attr_native_value = "overdue"
                else:
                    # Check last taken
                    last_taken_str = med_data.get("last_taken")
                    if last_taken_str:
                        try:
                            last_taken = datetime.fromisoformat(last_taken_str)
                            # If taken within last 6 hours, show as taken
                            if (now - last_taken).total_seconds() < 21600:
                                self._attr_native_value = "taken"
                            else:
                                self._attr_native_value = "scheduled"
                        except (ValueError, TypeError):
                            self._attr_native_value = "scheduled"
                    else:
                        self._attr_native_value = "scheduled"
            else:
                self._attr_native_value = "scheduled"

        self.async_write_ha_state()
