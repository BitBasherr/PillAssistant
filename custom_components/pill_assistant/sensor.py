"""Sensor platform for Pill Assistant."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    CONF_NOTES,
    ATTR_MEDICATION_ID,
    ATTR_NEXT_DOSE_TIME,
    ATTR_LAST_TAKEN,
    ATTR_REMAINING_AMOUNT,
    ATTR_SCHEDULE,
    ATTR_MISSED_DOSES,
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
        self._attr_name = entry.data.get(CONF_MEDICATION_NAME, "Unknown Medication")
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._state = "scheduled"
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
    def state(self) -> str:
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        if self._state == "due":
            return "mdi:pill"
        elif self._state == "taken":
            return "mdi:check-circle"
        elif self._state == "overdue":
            return "mdi:alert-circle"
        elif self._state == "refill_needed":
            return "mdi:package-variant"
        return "mdi:calendar-clock"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        storage_data = self._store_data["storage_data"]
        med_data = storage_data["medications"].get(self._medication_id, {})

        schedule_times = self._entry.data.get(CONF_SCHEDULE_TIMES, [])
        schedule_days = self._entry.data.get(CONF_SCHEDULE_DAYS, [])

        attributes = {
            ATTR_MEDICATION_ID: self._medication_id,
            CONF_DOSAGE: self._entry.data.get(CONF_DOSAGE, ""),
            CONF_DOSAGE_UNIT: self._entry.data.get(CONF_DOSAGE_UNIT, ""),
            ATTR_SCHEDULE: {
                "times": schedule_times,
                "days": schedule_days,
            },
            ATTR_REMAINING_AMOUNT: med_data.get("remaining_amount", 0),
            ATTR_LAST_TAKEN: med_data.get("last_taken"),
            CONF_REFILL_AMOUNT: self._entry.data.get(CONF_REFILL_AMOUNT, 0),
            CONF_REFILL_REMINDER_DAYS: self._entry.data.get(
                CONF_REFILL_REMINDER_DAYS, 0
            ),
            CONF_NOTES: self._entry.data.get(CONF_NOTES, ""),
        }

        # Calculate next dose time
        next_dose = self._calculate_next_dose()
        if next_dose:
            attributes[ATTR_NEXT_DOSE_TIME] = next_dose.isoformat()

        # Get missed doses
        missed_doses = self._get_missed_doses()
        if missed_doses:
            attributes[ATTR_MISSED_DOSES] = missed_doses

        return attributes

    def _calculate_next_dose(self) -> datetime | None:
        """Calculate the next dose time."""
        schedule_times = self._entry.data.get(CONF_SCHEDULE_TIMES, [])
        schedule_days = self._entry.data.get(CONF_SCHEDULE_DAYS, [])

        if not schedule_times or not schedule_days:
            return None

        now = dt_util.now()
        current_day = now.strftime("%a").lower()[:3]

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
        refill_amount = self._entry.data.get(CONF_REFILL_AMOUNT, 0)
        refill_reminder_days = self._entry.data.get(CONF_REFILL_REMINDER_DAYS, 7)

        # Calculate if refill is needed
        # Assuming one dose per scheduled time
        schedule_times = self._entry.data.get(CONF_SCHEDULE_TIMES, [])
        schedule_days = self._entry.data.get(CONF_SCHEDULE_DAYS, [])
        doses_per_week = len(schedule_times) * len(schedule_days)
        doses_per_day = doses_per_week / 7 if schedule_days else 0
        days_remaining = remaining / doses_per_day if doses_per_day > 0 else 0

        if days_remaining <= refill_reminder_days:
            self._state = "refill_needed"
        else:
            # Check if dose is due
            next_dose = self._calculate_next_dose()
            now = dt_util.now()

            if next_dose:
                time_to_dose = (next_dose - now).total_seconds()

                # Due if within 30 minutes
                if 0 <= time_to_dose <= 1800:
                    self._state = "due"
                # Overdue if missed by more than 30 minutes
                elif time_to_dose < 0:
                    self._state = "overdue"
                else:
                    # Check last taken
                    last_taken_str = med_data.get("last_taken")
                    if last_taken_str:
                        try:
                            last_taken = datetime.fromisoformat(last_taken_str)
                            # If taken within last 6 hours, show as taken
                            if (now - last_taken).total_seconds() < 21600:
                                self._state = "taken"
                            else:
                                self._state = "scheduled"
                        except (ValueError, TypeError):
                            self._state = "scheduled"
                    else:
                        self._state = "scheduled"
            else:
                self._state = "scheduled"

        self.async_write_ha_state()
