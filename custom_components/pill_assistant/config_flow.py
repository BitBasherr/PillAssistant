"""Config flow for Pill Assistant."""

from __future__ import annotations

import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
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
    CONF_NOTIFY_SERVICES,
    CONF_SNOOZE_DURATION_MINUTES,
    DEFAULT_DOSAGE_UNIT,
    DEFAULT_REFILL_REMINDER_DAYS,
    DEFAULT_SCHEDULE_DAYS,
    DEFAULT_SCHEDULE_TYPE,
    DEFAULT_SNOOZE_DURATION_MINUTES,
    DEFAULT_RELATIVE_OFFSET_HOURS,
    DEFAULT_RELATIVE_OFFSET_MINUTES,
    SCHEDULE_TYPE_OPTIONS,
    SELECT_DOSAGE_UNIT,
    SELECT_DAYS,
    SELECT_TIME,
)


def normalize_time_input(time_str: str) -> tuple[str | None, bool]:
    """
    Normalize time input to HH:MM format.
    
    Returns tuple of (normalized_time, needs_ampm_clarification)
    - If time is unambiguous (uses 24-hour or has AM/PM), returns (time, False)
    - If time needs clarification (e.g., "1015"), returns (time_without_ampm, True)
    - If invalid, returns (None, False)
    """
    time_str = time_str.strip().upper()
    
    # Check if it already has AM/PM
    has_ampm = "AM" in time_str or "PM" in time_str
    is_pm = "PM" in time_str
    
    # Check if it already contains a colon (standard format)
    has_colon = ":" in time_str
    
    # Remove AM/PM for processing
    time_str = time_str.replace("AM", "").replace("PM", "").strip()
    
    # If it has a colon, parse as HH:MM
    if has_colon:
        # Remove any hyphens
        time_str = time_str.replace("-", "")
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                return None, False
            hours = int(parts[0])
            minutes = int(parts[1])
        except (ValueError, IndexError):
            return None, False
    else:
        # Remove any hyphens or colons
        time_str = time_str.replace("-", "").replace(":", "")
        
        # Try to parse numeric time
        if not time_str.isdigit():
            return None, False
        
        # Handle different length inputs
        if len(time_str) == 3:  # e.g., "915" -> "09:15"
            hours = int(time_str[0])
            minutes = int(time_str[1:])
        elif len(time_str) == 4:  # e.g., "1015" -> "10:15"
            hours = int(time_str[:2])
            minutes = int(time_str[2:])
        elif len(time_str) == 1 or len(time_str) == 2:  # e.g., "9" or "10" -> hour only
            hours = int(time_str)
            minutes = 0
        else:
            return None, False
    
    # Validate hours and minutes
    if minutes < 0 or minutes > 59:
        return None, False
    
    # If has AM/PM, convert to 24-hour
    if has_ampm:
        if hours < 1 or hours > 12:
            return None, False
        if is_pm and hours != 12:
            hours += 12
        elif not is_pm and hours == 12:
            hours = 0
        return f"{hours:02d}:{minutes:02d}", False
    
    # Check if time is ambiguous (needs AM/PM clarification)
    # If it was already in HH:MM format with leading zero or > 12, it's 24-hour format
    if has_colon and (hours >= 13 or hours == 0):
        # Clear 24-hour format
        return f"{hours:02d}:{minutes:02d}", False
    elif has_colon and 1 <= hours <= 12:
        # Standard time format with colon but ambiguous hours - treat as 24-hour
        # This handles cases like "08:00" which users intend as 8 AM in 24-hour format
        return f"{hours:02d}:{minutes:02d}", False
    elif not has_colon and 1 <= hours <= 12:
        # No colon format is ambiguous - could be AM or PM
        return f"{hours:02d}:{minutes:02d}", True
    elif 0 <= hours <= 23:
        # Clear 24-hour format
        return f"{hours:02d}:{minutes:02d}", False
    else:
        return None, False


class PillAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pill Assistant."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}
        self._pending_times = []  # Times waiting for AM/PM clarification

    def _get_notify_services(self):
        """Get list of available notify services."""
        services = []
        if hasattr(self, "hass") and self.hass:
            # Get all services from the notify domain
            notify_services = self.hass.services.async_services().get("notify", {})
            for service_name in notify_services.keys():
                if service_name != "persistent_notification":
                    services.append(f"notify.{service_name}")
        return services

    async def async_step_user(self, user_input=None):
        """Handle the initial step - medication details."""
        errors = {}

        if user_input is not None:
            # Validate medication name
            if not user_input.get(CONF_MEDICATION_NAME):
                errors["base"] = "medication_name_required"
            else:
                self._data.update(user_input)
                return await self.async_step_schedule()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MEDICATION_NAME): str,
                    vol.Required(CONF_DOSAGE, default="1"): str,
                    vol.Required(
                        CONF_DOSAGE_UNIT, default=DEFAULT_DOSAGE_UNIT
                    ): SELECT_DOSAGE_UNIT,
                    vol.Optional(CONF_NOTES, default=""): str,
                }
            ),
            errors=errors,
        )

    async def async_step_schedule(self, user_input=None):
        """Handle the schedule step - choose schedule type."""
        errors = {}

        if user_input is not None:
            schedule_type = user_input.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE)
            self._data.update(user_input)

            # Route to appropriate schedule configuration step
            if schedule_type == "fixed_time":
                return await self.async_step_schedule_fixed()
            elif schedule_type == "relative_medication":
                return await self.async_step_schedule_relative_medication()
            elif schedule_type == "relative_sensor":
                return await self.async_step_schedule_relative_sensor()

        return self.async_show_form(
            step_id="schedule",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCHEDULE_TYPE, default=DEFAULT_SCHEDULE_TYPE
                    ): selector(
                        {
                            "select": {
                                "options": SCHEDULE_TYPE_OPTIONS,
                                "mode": "dropdown",
                            }
                        }
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "schedule_help": "Choose how to schedule this medication"
            },
        )

    async def async_step_schedule_fixed(self, user_input=None):
        """Handle fixed time schedule configuration."""
        errors = {}

        if user_input is not None:
            # Convert schedule_times to list if it's a single value
            schedule_times = user_input.get(CONF_SCHEDULE_TIMES, [])
            if isinstance(schedule_times, str):
                schedule_times = [schedule_times]
            
            # Normalize and validate time inputs
            normalized_times = []
            ambiguous_times = []
            
            for time_str in schedule_times:
                normalized, needs_clarification = normalize_time_input(time_str)
                if normalized is None:
                    errors["base"] = "invalid_time_format"
                    break
                elif needs_clarification:
                    ambiguous_times.append((time_str, normalized))
                else:
                    normalized_times.append(normalized)
            
            if not errors:
                # Store normalized times and other data
                user_input[CONF_SCHEDULE_TIMES] = normalized_times
                
                # Ensure schedule_days is set
                if not user_input.get(CONF_SCHEDULE_DAYS):
                    user_input[CONF_SCHEDULE_DAYS] = DEFAULT_SCHEDULE_DAYS
                
                self._data.update(user_input)
                
                # If there are ambiguous times, go to clarification step
                if ambiguous_times:
                    self._pending_times = ambiguous_times
                    return await self.async_step_time_clarification()
                
                return await self.async_step_refill()

        return self.async_show_form(
            step_id="schedule_fixed",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCHEDULE_TIMES): selector(
                        {
                            "select": {
                                "options": [],
                                "custom_value": True,
                                "multiple": True,
                                "mode": "dropdown",
                            }
                        }
                    ),
                    vol.Required(
                        CONF_SCHEDULE_DAYS, default=DEFAULT_SCHEDULE_DAYS
                    ): SELECT_DAYS,
                }
            ),
            errors=errors,
            description_placeholders={
                "schedule_times_example": "Enter times like 1015, 8:00AM, 2030, or 20:30"
            },
        )

    async def async_step_time_clarification(self, user_input=None):
        """Clarify AM/PM for ambiguous times."""
        errors = {}
        
        if user_input is not None:
            # Process the AM/PM choices for each pending time
            clarified_times = []
            for i, (original, normalized) in enumerate(self._pending_times):
                choice_key = f"time_{i}_ampm"
                ampm_choice = user_input.get(choice_key, "AM")
                
                # Parse the normalized time and convert based on AM/PM
                hours, minutes = map(int, normalized.split(":"))
                
                if ampm_choice == "PM" and hours != 12:
                    hours += 12
                elif ampm_choice == "AM" and hours == 12:
                    hours = 0
                    
                clarified_times.append(f"{hours:02d}:{minutes:02d}")
            
            # Add clarified times to the existing times
            existing_times = self._data.get(CONF_SCHEDULE_TIMES, [])
            self._data[CONF_SCHEDULE_TIMES] = existing_times + clarified_times
            self._pending_times = []
            
            return await self.async_step_refill()
        
        # Build schema for clarification
        schema_dict = {}
        description_lines = ["Please clarify if these times are AM or PM:"]
        
        for i, (original, normalized) in enumerate(self._pending_times):
            choice_key = f"time_{i}_ampm"
            description_lines.append(f"- {original} (entered as {normalized})")
            
            schema_dict[vol.Required(choice_key, default="AM")] = selector(
                {
                    "select": {
                        "options": ["AM", "PM"],
                        "mode": "dropdown",
                    }
                }
            )
        
        return self.async_show_form(
            step_id="time_clarification",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "clarification_help": "\n".join(description_lines)
            },
        )

    async def async_step_schedule_relative_medication(self, user_input=None):
        """Handle relative to medication schedule configuration."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_refill()

        # Get list of existing medications to choose from
        existing_meds = []
        if self.hass:
            # Get all config entries for this domain
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                med_name = entry.data.get(CONF_MEDICATION_NAME, "Unknown")
                existing_meds.append({"label": med_name, "value": entry.entry_id})

        schema_dict = {
            vol.Required(
                CONF_RELATIVE_OFFSET_HOURS, default=DEFAULT_RELATIVE_OFFSET_HOURS
            ): vol.Coerce(int),
            vol.Required(
                CONF_RELATIVE_OFFSET_MINUTES, default=DEFAULT_RELATIVE_OFFSET_MINUTES
            ): vol.Coerce(int),
            vol.Required(
                CONF_SCHEDULE_DAYS, default=DEFAULT_SCHEDULE_DAYS
            ): SELECT_DAYS,
        }

        # Add medication selector if medications exist
        if existing_meds:
            schema_dict[vol.Required(CONF_RELATIVE_TO_MEDICATION)] = selector(
                {
                    "select": {
                        "options": existing_meds,
                        "mode": "dropdown",
                    }
                }
            )

        return self.async_show_form(
            step_id="schedule_relative_medication",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "help": "Take this medication X hours/minutes after another medication"
            },
        )

    async def async_step_schedule_relative_sensor(self, user_input=None):
        """Handle relative to sensor schedule configuration."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_refill()

        return self.async_show_form(
            step_id="schedule_relative_sensor",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RELATIVE_TO_SENSOR): selector(
                        {
                            "entity": {
                                "domain": ["binary_sensor", "sensor"],
                            }
                        }
                    ),
                    vol.Required(
                        CONF_RELATIVE_OFFSET_HOURS,
                        default=DEFAULT_RELATIVE_OFFSET_HOURS,
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_RELATIVE_OFFSET_MINUTES,
                        default=DEFAULT_RELATIVE_OFFSET_MINUTES,
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_SCHEDULE_DAYS, default=DEFAULT_SCHEDULE_DAYS
                    ): SELECT_DAYS,
                }
            ),
            errors=errors,
            description_placeholders={
                "help": "Take this medication X hours/minutes after a sensor changes state (e.g., wake-up sensor)"
            },
        )

    async def async_step_refill(self, user_input=None):
        """Handle the refill step."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)

            # Create unique ID based on medication name
            await self.async_set_unique_id(
                f"{DOMAIN}_{self._data[CONF_MEDICATION_NAME].lower().replace(' ', '_')}"
            )
            self._abort_if_unique_id_configured()

            # Create the entry - button entity will be automatically created by button platform
            return self.async_create_entry(
                title=self._data[CONF_MEDICATION_NAME],
                data=self._data,
            )

        # Get available notification services
        notify_services = self._get_notify_services()
        notify_options = [{"label": svc, "value": svc} for svc in notify_services]

        schema_dict = {
            vol.Required(CONF_REFILL_AMOUNT, default=30): vol.Coerce(int),
            vol.Required(
                CONF_REFILL_REMINDER_DAYS, default=DEFAULT_REFILL_REMINDER_DAYS
            ): vol.Coerce(int),
            vol.Optional(
                CONF_SNOOZE_DURATION_MINUTES, default=DEFAULT_SNOOZE_DURATION_MINUTES
            ): vol.Coerce(int),
        }

        # Add notification service selector if services are available
        if notify_options:
            schema_dict[vol.Optional(CONF_NOTIFY_SERVICES, default=[])] = selector(
                {
                    "select": {
                        "options": notify_options,
                        "multiple": True,
                        "mode": "dropdown",
                    }
                }
            )

        return self.async_show_form(
            step_id="refill",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PillAssistantOptionsFlow(config_entry)


class PillAssistantOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Pill Assistant."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry
        self._pending_times = []  # Times waiting for AM/PM clarification
        self._temp_user_input = {}  # Temporary storage for user input during clarification

    def _get_notify_services(self):
        """Get list of available notify services."""
        services = []
        if self.hass:
            # Get all services from the notify domain
            notify_services = self.hass.services.async_services().get("notify", {})
            for service_name in notify_services.keys():
                if service_name != "persistent_notification":
                    services.append(f"notify.{service_name}")
        return services

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            # If schedule_type is fixed_time, validate and normalize times
            schedule_type = user_input.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE)
            errors = {}
            
            if schedule_type == "fixed_time":
                schedule_times = user_input.get(CONF_SCHEDULE_TIMES, [])
                if isinstance(schedule_times, str):
                    schedule_times = [schedule_times]
                
                # Normalize and validate time inputs
                normalized_times = []
                ambiguous_times = []
                
                for time_str in schedule_times:
                    normalized, needs_clarification = normalize_time_input(time_str)
                    if normalized is None:
                        errors["base"] = "invalid_time_format"
                        break
                    elif needs_clarification:
                        ambiguous_times.append((time_str, normalized))
                    else:
                        normalized_times.append(normalized)
                
                if not errors:
                    user_input[CONF_SCHEDULE_TIMES] = normalized_times
                    
                    # If there are ambiguous times, go to clarification step
                    if ambiguous_times:
                        self._pending_times = ambiguous_times
                        self._temp_user_input = user_input
                        return await self.async_step_time_clarification_options()
            
            if not errors:
                # Update the config entry with new data
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data={**self._config_entry.data, **user_input},
                )

                return self.async_create_entry(title="", data={})
            else:
                # Re-show form with errors
                pass

        current_data = self._config_entry.data
        schedule_type = current_data.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE)

        # Get available notification services
        notify_services = self._get_notify_services()
        notify_options = [{"label": svc, "value": svc} for svc in notify_services]

        # Base schema
        schema_dict = {
            vol.Required(
                CONF_MEDICATION_NAME,
                default=current_data.get(CONF_MEDICATION_NAME, ""),
            ): str,
            vol.Required(CONF_DOSAGE, default=current_data.get(CONF_DOSAGE, "1")): str,
            vol.Required(
                CONF_DOSAGE_UNIT,
                default=current_data.get(CONF_DOSAGE_UNIT, DEFAULT_DOSAGE_UNIT),
            ): SELECT_DOSAGE_UNIT,
            vol.Required(
                CONF_SCHEDULE_TYPE,
                default=schedule_type,
            ): selector(
                {
                    "select": {
                        "options": SCHEDULE_TYPE_OPTIONS,
                        "mode": "dropdown",
                    }
                }
            ),
        }

        # Add schedule-type specific fields
        if schedule_type == "fixed_time":
            schema_dict[
                vol.Required(
                    CONF_SCHEDULE_TIMES,
                    default=current_data.get(CONF_SCHEDULE_TIMES, []),
                )
            ] = selector(
                {
                    "select": {
                        "options": [],
                        "custom_value": True,
                        "multiple": True,
                        "mode": "dropdown",
                    }
                }
            )
        elif schedule_type == "relative_medication":
            # Get list of medications
            existing_meds = []
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id != self._config_entry.entry_id:
                    med_name = entry.data.get(CONF_MEDICATION_NAME, "Unknown")
                    existing_meds.append({"label": med_name, "value": entry.entry_id})

            if existing_meds:
                schema_dict[
                    vol.Required(
                        CONF_RELATIVE_TO_MEDICATION,
                        default=current_data.get(
                            CONF_RELATIVE_TO_MEDICATION,
                            existing_meds[0]["value"] if existing_meds else "",
                        ),
                    )
                ] = selector(
                    {
                        "select": {
                            "options": existing_meds,
                            "mode": "dropdown",
                        }
                    }
                )

            schema_dict[
                vol.Required(
                    CONF_RELATIVE_OFFSET_HOURS,
                    default=current_data.get(
                        CONF_RELATIVE_OFFSET_HOURS, DEFAULT_RELATIVE_OFFSET_HOURS
                    ),
                )
            ] = vol.Coerce(int)
            schema_dict[
                vol.Required(
                    CONF_RELATIVE_OFFSET_MINUTES,
                    default=current_data.get(
                        CONF_RELATIVE_OFFSET_MINUTES, DEFAULT_RELATIVE_OFFSET_MINUTES
                    ),
                )
            ] = vol.Coerce(int)
        elif schedule_type == "relative_sensor":
            schema_dict[
                vol.Required(
                    CONF_RELATIVE_TO_SENSOR,
                    default=current_data.get(CONF_RELATIVE_TO_SENSOR, ""),
                )
            ] = selector(
                {
                    "entity": {
                        "domain": ["binary_sensor", "sensor"],
                    }
                }
            )
            schema_dict[
                vol.Required(
                    CONF_RELATIVE_OFFSET_HOURS,
                    default=current_data.get(
                        CONF_RELATIVE_OFFSET_HOURS, DEFAULT_RELATIVE_OFFSET_HOURS
                    ),
                )
            ] = vol.Coerce(int)
            schema_dict[
                vol.Required(
                    CONF_RELATIVE_OFFSET_MINUTES,
                    default=current_data.get(
                        CONF_RELATIVE_OFFSET_MINUTES, DEFAULT_RELATIVE_OFFSET_MINUTES
                    ),
                )
            ] = vol.Coerce(int)

        # Add common fields
        schema_dict[
            vol.Required(
                CONF_SCHEDULE_DAYS,
                default=current_data.get(CONF_SCHEDULE_DAYS, DEFAULT_SCHEDULE_DAYS),
            )
        ] = SELECT_DAYS
        schema_dict[
            vol.Required(
                CONF_REFILL_AMOUNT,
                default=current_data.get(CONF_REFILL_AMOUNT, 30),
            )
        ] = vol.Coerce(int)
        schema_dict[
            vol.Required(
                CONF_REFILL_REMINDER_DAYS,
                default=current_data.get(
                    CONF_REFILL_REMINDER_DAYS, DEFAULT_REFILL_REMINDER_DAYS
                ),
            )
        ] = vol.Coerce(int)
        schema_dict[
            vol.Optional(
                CONF_SNOOZE_DURATION_MINUTES,
                default=current_data.get(
                    CONF_SNOOZE_DURATION_MINUTES, DEFAULT_SNOOZE_DURATION_MINUTES
                ),
            )
        ] = vol.Coerce(int)
        schema_dict[
            vol.Optional(CONF_NOTES, default=current_data.get(CONF_NOTES, ""))
        ] = str

        # Add notification service selector if services are available
        if notify_options:
            schema_dict[
                vol.Optional(
                    CONF_NOTIFY_SERVICES,
                    default=current_data.get(CONF_NOTIFY_SERVICES, []),
                )
            ] = selector(
                {
                    "select": {
                        "options": notify_options,
                        "multiple": True,
                        "mode": "dropdown",
                    }
                }
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_time_clarification_options(self, user_input=None):
        """Clarify AM/PM for ambiguous times in options flow."""
        errors = {}
        
        if user_input is not None:
            # Process the AM/PM choices for each pending time
            clarified_times = []
            for i, (original, normalized) in enumerate(self._pending_times):
                choice_key = f"time_{i}_ampm"
                ampm_choice = user_input.get(choice_key, "AM")
                
                # Parse the normalized time and convert based on AM/PM
                hours, minutes = map(int, normalized.split(":"))
                
                if ampm_choice == "PM" and hours != 12:
                    hours += 12
                elif ampm_choice == "AM" and hours == 12:
                    hours = 0
                    
                clarified_times.append(f"{hours:02d}:{minutes:02d}")
            
            # Add clarified times to the existing times
            existing_times = self._temp_user_input.get(CONF_SCHEDULE_TIMES, [])
            self._temp_user_input[CONF_SCHEDULE_TIMES] = existing_times + clarified_times
            self._pending_times = []
            
            # Update the config entry with new data
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={**self._config_entry.data, **self._temp_user_input},
            )
            
            return self.async_create_entry(title="", data={})
        
        # Build schema for clarification
        schema_dict = {}
        description_lines = ["Please clarify if these times are AM or PM:"]
        
        for i, (original, normalized) in enumerate(self._pending_times):
            choice_key = f"time_{i}_ampm"
            description_lines.append(f"- {original} (entered as {normalized})")
            
            schema_dict[vol.Required(choice_key, default="AM")] = selector(
                {
                    "select": {
                        "options": ["AM", "PM"],
                        "mode": "dropdown",
                    }
                }
            )
        
        return self.async_show_form(
            step_id="time_clarification_options",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "clarification_help": "\n".join(description_lines)
            },
        )
