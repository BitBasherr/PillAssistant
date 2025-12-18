"""Sensor platform for Pill Assistant."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN,
    LOG_FILE_NAME,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TYPE,
    CONF_RELATIVE_TO_MEDICATION,
    CONF_RELATIVE_TO_SENSOR,
    CONF_RELATIVE_OFFSET_HOURS,
    CONF_RELATIVE_OFFSET_MINUTES,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    CONF_NOTES,
    DEFAULT_SCHEDULE_TYPE,
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

_LOGGER = logging.getLogger(__name__)


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
        self._attr_name = f"PA_{self._medication_name}"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_native_value = "scheduled"
        self._medication_id = entry.entry_id

        # Get storage data
        self._store_data = hass.data[DOMAIN][entry.entry_id]

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
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
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._medication_id)},
            "name": f"Pill Assistant - {self._medication_name}",
            "manufacturer": "Pill Assistant",
            "model": "Medication Tracker",
        }

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

        # Get log file location
        log_path = self.hass.config.path(LOG_FILE_NAME)

        # Use human-friendly keys as per requirements but keep backward compatibility
        attributes = {
            # Human-friendly attribute names
            ATTR_DISPLAY_MEDICATION_ID: self._medication_id,
            "Dosage": f"{self._entry.data.get(CONF_DOSAGE, '')} {self._entry.data.get(CONF_DOSAGE_UNIT, '')}",
            ATTR_SCHEDULE: schedule_str,
            ATTR_REMAINING_AMOUNT: med_data.get("remaining_amount", 0),
            ATTR_LAST_TAKEN: med_data.get("last_taken") or "Never",
            "Refill amount": self._entry.data.get(CONF_REFILL_AMOUNT, 0),
            "Refill reminder days": self._entry.data.get(CONF_REFILL_REMINDER_DAYS, 0),
            ATTR_DOSES_TAKEN_TODAY: doses_today,
            ATTR_TAKEN_SCHEDULED_RATIO: ratio_str,
            ATTR_LOG_FILE_LOCATION: log_path,
            # Keep backward-compatible keys for existing automations
            "remaining_amount": med_data.get("remaining_amount", 0),
            "last_taken": med_data.get("last_taken"),
            "dosage": self._entry.data.get(CONF_DOSAGE, ""),
            "dosage_unit": self._entry.data.get(CONF_DOSAGE_UNIT, ""),
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
            return f"{offset_hours}h {offset_minutes}m after {rel_med_name}"
        elif schedule_type == "relative_sensor":
            sensor_id = self._entry.data.get(CONF_RELATIVE_TO_SENSOR, "unknown sensor")
            offset_hours = self._entry.data.get(CONF_RELATIVE_OFFSET_HOURS, 0)
            offset_minutes = self._entry.data.get(CONF_RELATIVE_OFFSET_MINUTES, 0)
            return f"{offset_hours}h {offset_minutes}m after {sensor_id}"
        return "Unknown schedule type"

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

        if not sensor_entity_id:
            return None

        # Get the sensor's last changed time
        sensor_state = self.hass.states.get(sensor_entity_id)
        if not sensor_state:
            return None

        sensor_last_changed = sensor_state.last_changed
        if not sensor_last_changed:
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
                    med_data["snooze_until"] = None
                    store = self._store_data["store"]
                    await store.async_save(storage_data)
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
                    self._attr_native_value = "due"
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
