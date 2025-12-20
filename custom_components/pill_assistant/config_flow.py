"""Config flow for Pill Assistant."""

from __future__ import annotations

from datetime import timedelta

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_MEDICATION_TYPE,
    CONF_STRENGTH,
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
    CONF_CURRENT_QUANTITY,
    CONF_USE_CUSTOM_QUANTITY,
    CONF_NOTES,
    CONF_NOTIFY_SERVICES,
    CONF_SNOOZE_DURATION_MINUTES,
    CONF_ENABLE_AUTOMATIC_NOTIFICATIONS,
    CONF_ON_TIME_WINDOW_MINUTES,
    DEFAULT_DOSAGE_UNIT,
    DEFAULT_MEDICATION_TYPE,
    DEFAULT_STRENGTH,
    DEFAULT_REFILL_REMINDER_DAYS,
    DEFAULT_SCHEDULE_DAYS,
    DEFAULT_SCHEDULE_TYPE,
    DEFAULT_SNOOZE_DURATION_MINUTES,
    DEFAULT_RELATIVE_OFFSET_HOURS,
    DEFAULT_RELATIVE_OFFSET_MINUTES,
    DEFAULT_SENSOR_TRIGGER_VALUE,
    DEFAULT_SENSOR_TRIGGER_ATTRIBUTE,
    DEFAULT_AVOID_DUPLICATE_TRIGGERS,
    DEFAULT_IGNORE_UNAVAILABLE,
    DEFAULT_ENABLE_AUTOMATIC_NOTIFICATIONS,
    DEFAULT_ON_TIME_WINDOW_MINUTES,
    MAX_SENSOR_HISTORY_CHANGES,
    SCHEDULE_TYPE_OPTIONS,
    SELECT_MEDICATION_TYPE,
    SELECT_DOSAGE_UNIT,
    SELECT_DAYS,
    LEGACY_DOSAGE_UNITS,
    DOSAGE_UNIT_OPTIONS,
)


def migrate_legacy_dosage_unit(data: dict) -> dict:
    """
    Migrate legacy dosage_unit to separate medication_type and dosage_unit.

    This handles upgrading configurations that used the old combined format
    (e.g., "pill(s)", "tablet(s)") to the new separate fields.

    Returns a new dict with migrated data.
    """
    if CONF_MEDICATION_TYPE in data:
        # Already migrated
        return data

    migrated_data = data.copy()
    dosage_unit = data.get(CONF_DOSAGE_UNIT, DEFAULT_DOSAGE_UNIT)

    # Check if this is a legacy dosage unit
    if dosage_unit in LEGACY_DOSAGE_UNITS:
        med_type, unit = LEGACY_DOSAGE_UNITS[dosage_unit]
        migrated_data[CONF_MEDICATION_TYPE] = med_type
        migrated_data[CONF_DOSAGE_UNIT] = unit
    else:
        # Unknown format - assign defaults
        migrated_data[CONF_MEDICATION_TYPE] = DEFAULT_MEDICATION_TYPE
        # Keep the existing dosage_unit if it's valid, otherwise use default
        valid_units = [opt["value"] for opt in DOSAGE_UNIT_OPTIONS]
        if dosage_unit not in valid_units:
            migrated_data[CONF_DOSAGE_UNIT] = DEFAULT_DOSAGE_UNIT

    return migrated_data


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
    if minutes < 0 or minutes > 59 or hours < 0 or hours > 23:
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
                        CONF_MEDICATION_TYPE, default=DEFAULT_MEDICATION_TYPE
                    ): SELECT_MEDICATION_TYPE,
                    vol.Optional(CONF_STRENGTH, default=DEFAULT_STRENGTH): str,
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
            # Check if sensor is being selected for the first time
            sensor_just_selected = (
                CONF_RELATIVE_TO_SENSOR in user_input
                and self._data.get(CONF_RELATIVE_TO_SENSOR)
                != user_input.get(CONF_RELATIVE_TO_SENSOR)
            )

            self._data.update(user_input)

            # If sensor was just selected, re-show form with additional options
            if sensor_just_selected:
                pass  # Fall through to show form again with full options
            else:
                # All data collected, proceed to next step
                return await self.async_step_refill()

        # Build sensor information display if a sensor has been selected
        sensor_info = ""
        sensor_entity_id = self._data.get(CONF_RELATIVE_TO_SENSOR)

        if sensor_entity_id:
            sensor_state = self.hass.states.get(sensor_entity_id)
            if sensor_state:
                # Get current state and last changed
                current_value = sensor_state.state
                last_changed = sensor_state.last_changed

                # Convert to local time
                local_time = dt_util.as_local(last_changed)
                last_changed_str = local_time.strftime("%Y-%m-%d %H:%M:%S")

                # Build sensor info display
                sensor_info = f"**Current Entity Information:**\n\n"
                sensor_info += f"**Entity ID:** `{sensor_entity_id}`\n"
                sensor_info += f"**Current State:** `{current_value}`\n"
                sensor_info += f"**Last Changed:** {last_changed_str}\n"

                # Show available attributes
                if sensor_state.attributes:
                    sensor_info += f"**Available Attributes:**\n"
                    for attr_name, attr_value in list(sensor_state.attributes.items())[
                        :10
                    ]:  # Limit to first 10
                        if attr_name not in ["friendly_name", "icon", "device_class"]:
                            sensor_info += f"  • `{attr_name}`: {attr_value}\n"
                    sensor_info += "\n"

                # Get state history for last 24 hours
                now = dt_util.now()
                start_time = now - timedelta(hours=24)

                # Get history using recorder component with error handling
                try:
                    from homeassistant.components import history

                    history_states = await self.hass.async_add_executor_job(
                        history.state_changes_during_period,
                        self.hass,
                        start_time,
                        now,
                        sensor_entity_id,
                    )

                    if history_states and sensor_entity_id in history_states:
                        state_changes = history_states[sensor_entity_id]

                        if len(state_changes) > 1:
                            sensor_info += (
                                f"**State Changes (Last 24 Hours):**\n\n```\n"
                            )

                            # Show state changes in reverse chronological order (newest first)
                            for state in reversed(
                                state_changes[-MAX_SENSOR_HISTORY_CHANGES:]
                            ):
                                change_time = dt_util.as_local(state.last_changed)
                                change_time_str = change_time.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                                sensor_info += f"• {change_time_str} → {state.state}\n"

                            sensor_info += "```\n"
                        else:
                            sensor_info += "*No state changes in the last 24 hours.*\n"
                    else:
                        sensor_info += "*No state history available.*\n"
                except (ImportError, Exception) as ex:
                    # History/recorder component not available or error fetching history
                    sensor_info += (
                        f"*State history unavailable (recorder may be disabled).*\n"
                    )

                # Detect sensor type and offer trigger value options
                sensor_type = self._detect_sensor_type(sensor_state)
                trigger_value_options = self._get_trigger_value_options(
                    sensor_state, sensor_type
                )

        # Build schema - allow ALL entity types
        schema_dict = {
            vol.Required(CONF_RELATIVE_TO_SENSOR): selector(
                {"entity": {}}  # No domain restriction - all entities allowed
            ),
        }

        # Add trigger value selector if sensor is selected
        if sensor_entity_id and sensor_state:
            trigger_value_options = self._get_trigger_value_options(
                sensor_state, self._detect_sensor_type(sensor_state)
            )
            if trigger_value_options:
                schema_dict[
                    vol.Optional(
                        CONF_SENSOR_TRIGGER_VALUE,
                        default=DEFAULT_SENSOR_TRIGGER_VALUE,
                    )
                ] = selector(
                    {
                        "select": {
                            "options": trigger_value_options,
                            "mode": "dropdown",
                            "custom_value": True,
                        }
                    }
                )
            else:
                # Allow free text input for custom trigger values
                schema_dict[
                    vol.Optional(
                        CONF_SENSOR_TRIGGER_VALUE,
                        default=DEFAULT_SENSOR_TRIGGER_VALUE,
                    )
                ] = selector({"text": {}})

            # Add attribute selector if entity has attributes
            if sensor_state.attributes:
                # Get list of non-standard attributes
                available_attrs = [
                    {"label": "State (default)", "value": ""},
                ]
                for attr_name in sensor_state.attributes.keys():
                    if attr_name not in [
                        "friendly_name",
                        "icon",
                        "device_class",
                        "unit_of_measurement",
                    ]:
                        available_attrs.append({"label": attr_name, "value": attr_name})

                if len(available_attrs) > 1:  # More than just "State"
                    schema_dict[
                        vol.Optional(
                            CONF_SENSOR_TRIGGER_ATTRIBUTE,
                            default=DEFAULT_SENSOR_TRIGGER_ATTRIBUTE,
                        )
                    ] = selector(
                        {
                            "select": {
                                "options": available_attrs,
                                "mode": "dropdown",
                            }
                        }
                    )

        schema_dict.update(
            {
                vol.Required(
                    CONF_RELATIVE_OFFSET_HOURS,
                    default=DEFAULT_RELATIVE_OFFSET_HOURS,
                ): vol.Coerce(int),
                vol.Required(
                    CONF_RELATIVE_OFFSET_MINUTES,
                    default=DEFAULT_RELATIVE_OFFSET_MINUTES,
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_AVOID_DUPLICATE_TRIGGERS,
                    default=DEFAULT_AVOID_DUPLICATE_TRIGGERS,
                ): selector({"boolean": {}}),
                vol.Optional(
                    CONF_IGNORE_UNAVAILABLE,
                    default=DEFAULT_IGNORE_UNAVAILABLE,
                ): selector({"boolean": {}}),
                vol.Required(
                    CONF_SCHEDULE_DAYS, default=DEFAULT_SCHEDULE_DAYS
                ): SELECT_DAYS,
            }
        )

        return self.async_show_form(
            step_id="schedule_relative_sensor",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "help": f"{sensor_info}\n**Configure Entity-Based Scheduling:**\n\nTake this medication X hours/minutes after an entity changes state.\n\n**Trigger Value:** Specify which value should trigger the schedule (leave empty to trigger on any change).\n\n**Trigger Attribute:** Monitor a specific attribute instead of the entity state (optional).\n\n**Avoid Duplicate Triggers:** Prevents multiple schedules for the same event.\n\n**Ignore Unavailable:** When enabled, ignores 'unknown' and 'unavailable' states when monitoring for changes."
            },
        )

    def _detect_sensor_type(self, sensor_state):
        """Detect the type of sensor based on its attributes and state."""
        if not sensor_state:
            return "unknown"

        domain = sensor_state.entity_id.split(".")[0]

        # Binary sensors have on/off states
        if domain == "binary_sensor":
            return "binary"

        # Check attributes for sensor class
        attributes = sensor_state.attributes
        device_class = attributes.get("device_class")
        unit = attributes.get("unit_of_measurement")

        if device_class:
            return device_class

        # Try to detect from state value
        state_value = sensor_state.state

        # Check if numeric
        try:
            float(state_value)
            return "numeric"
        except (ValueError, TypeError):
            pass

        # Check common state patterns
        if state_value in ["on", "off", "true", "false", "open", "closed"]:
            return "binary_like"

        return "text"

    def _get_trigger_value_options(self, sensor_state, sensor_type):
        """Get appropriate trigger value options based on sensor type."""
        if not sensor_state:
            return []

        options = []

        if sensor_type == "binary" or sensor_type == "binary_like":
            # Binary sensors or sensors with binary-like values
            current_state = sensor_state.state.lower() if sensor_state.state else ""
            if current_state in ["on", "off"]:
                options = [
                    {"label": "On", "value": "on"},
                    {"label": "Off", "value": "off"},
                ]
            elif current_state in ["true", "false"]:
                options = [
                    {"label": "True", "value": "true"},
                    {"label": "False", "value": "false"},
                ]
            elif current_state in ["open", "closed"]:
                options = [
                    {"label": "Open", "value": "open"},
                    {"label": "Closed", "value": "closed"},
                ]
            else:
                # Provide both on and off as defaults
                options = [
                    {"label": "On", "value": "on"},
                    {"label": "Off", "value": "off"},
                ]
        elif sensor_type == "numeric":
            # For numeric sensors, user can enter custom values
            # Return empty to show text input
            return []
        else:
            # For other sensors, get unique values from history or use text input
            return []

        # Add "Any change" option at the beginning
        options.insert(0, {"label": "Any change (empty)", "value": ""})

        return options

    async def async_step_refill(self, user_input=None):
        """Handle the refill step."""
        errors = {}

        if user_input is not None:
            # Check if user wants custom quantity and hasn't provided it yet
            use_custom = user_input.get(CONF_USE_CUSTOM_QUANTITY, False)
            has_custom_quantity = CONF_CURRENT_QUANTITY in user_input

            if use_custom and not has_custom_quantity:
                # Re-show form with current quantity field
                self._data.update(user_input)
                pass  # Fall through to show form again
            else:
                self._data.update(user_input)

                # If not using custom quantity, set current quantity to refill amount
                if not use_custom:
                    self._data[CONF_CURRENT_QUANTITY] = self._data.get(
                        CONF_REFILL_AMOUNT, 30
                    )

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

        # Check if we should show the custom quantity field
        use_custom = self._data.get(CONF_USE_CUSTOM_QUANTITY, False)

        schema_dict = {
            vol.Required(
                CONF_REFILL_AMOUNT, default=self._data.get(CONF_REFILL_AMOUNT, 30)
            ): vol.Coerce(int),
            vol.Required(
                CONF_REFILL_REMINDER_DAYS,
                default=self._data.get(
                    CONF_REFILL_REMINDER_DAYS, DEFAULT_REFILL_REMINDER_DAYS
                ),
            ): vol.Coerce(int),
            vol.Optional(
                CONF_USE_CUSTOM_QUANTITY,
                default=self._data.get(CONF_USE_CUSTOM_QUANTITY, False),
            ): selector({"boolean": {}}),
        }

        # Add current quantity field if checkbox is checked
        if use_custom:
            schema_dict[
                vol.Required(
                    CONF_CURRENT_QUANTITY,
                    default=self._data.get(
                        CONF_CURRENT_QUANTITY, self._data.get(CONF_REFILL_AMOUNT, 30)
                    ),
                )
            ] = vol.Coerce(int)

        schema_dict.update(
            {
                vol.Optional(
                    CONF_SNOOZE_DURATION_MINUTES,
                    default=self._data.get(
                        CONF_SNOOZE_DURATION_MINUTES, DEFAULT_SNOOZE_DURATION_MINUTES
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_ENABLE_AUTOMATIC_NOTIFICATIONS,
                    default=self._data.get(
                        CONF_ENABLE_AUTOMATIC_NOTIFICATIONS,
                        DEFAULT_ENABLE_AUTOMATIC_NOTIFICATIONS,
                    ),
                ): selector({"boolean": {}}),
                vol.Optional(
                    CONF_ON_TIME_WINDOW_MINUTES,
                    default=self._data.get(
                        CONF_ON_TIME_WINDOW_MINUTES, DEFAULT_ON_TIME_WINDOW_MINUTES
                    ),
                ): vol.Coerce(int),
            }
        )

        # Add notification service selector if services are available
        if notify_options:
            schema_dict[
                vol.Optional(
                    CONF_NOTIFY_SERVICES,
                    default=self._data.get(CONF_NOTIFY_SERVICES, []),
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
            step_id="refill",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "help": "Configure refill settings.\n\n**Use Custom Starting Quantity**: Check this box if you're not starting with a full bottle at the refill amount. When checked, you can enter the actual current quantity you have."
            },
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
        self._temp_user_input = (
            {}
        )  # Temporary storage for user input during clarification
        self._temp_schedule_type = None  # Track schedule_type changes during flow

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
        errors = {}

        # Migrate legacy data on first access
        current_data = migrate_legacy_dosage_unit(self._config_entry.data)
        schedule_type_changed = False

        if user_input is not None:
            new_schedule_type = user_input.get(
                CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE
            )
            # Use temp schedule type if available, otherwise use config entry
            old_schedule_type = (
                self._temp_schedule_type
                if self._temp_schedule_type is not None
                else current_data.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE)
            )
            schedule_type_changed = new_schedule_type != old_schedule_type

            # If schedule type was changed, re-render the form with new fields
            # Don't save yet - let user fill in the new schedule-specific fields
            if schedule_type_changed:
                # Store the new schedule type for subsequent form renders
                self._temp_schedule_type = new_schedule_type
                # Update current_data with the new schedule_type for form rendering
                current_data = {**current_data, **user_input}
                schedule_type = new_schedule_type
                user_input = None  # Reset to trigger form re-render
            else:
                schedule_type = new_schedule_type
        else:
            # Use temp schedule type if available (after a schedule type change)
            schedule_type = (
                self._temp_schedule_type
                if self._temp_schedule_type is not None
                else current_data.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE)
            )
            # If we're using temp_schedule_type, update current_data to reflect it
            if self._temp_schedule_type is not None:
                current_data = {
                    **current_data,
                    CONF_SCHEDULE_TYPE: self._temp_schedule_type,
                }

        if user_input is not None:
            # Process the form submission (schedule_type was not changed)

            # If schedule_type is fixed_time, validate and normalize times
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
                # Get medication ID
                med_id = self._config_entry.entry_id

                # Update the config entry with new data
                # Clear temp schedule type since we're saving now
                self._temp_schedule_type = None
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data={**self._config_entry.data, **user_input},
                )

                # If remaining_amount was changed, update it in storage
                if CONF_CURRENT_QUANTITY in user_input:
                    from .const import DOMAIN as PILL_DOMAIN

                    if (
                        PILL_DOMAIN in self.hass.data
                        and med_id in self.hass.data[PILL_DOMAIN]
                    ):
                        entry_data = self.hass.data[PILL_DOMAIN][med_id]
                        storage_data = entry_data.get("storage_data", {})
                        medications = storage_data.get("medications", {})

                        if med_id in medications:
                            medications[med_id]["remaining_amount"] = user_input[
                                CONF_CURRENT_QUANTITY
                            ]
                            # Save to storage
                            store = entry_data.get("store")
                            if store:
                                await store.async_save(storage_data)

                return self.async_create_entry(title="", data={})

        # Get available notification services
        notify_services = self._get_notify_services()
        notify_options = [{"label": svc, "value": svc} for svc in notify_services]

        # Get current remaining amount from storage
        remaining_amount = 0
        med_id = self._config_entry.entry_id
        from .const import DOMAIN as PILL_DOMAIN

        if PILL_DOMAIN in self.hass.data and med_id in self.hass.data[PILL_DOMAIN]:
            entry_data = self.hass.data[PILL_DOMAIN][med_id]
            storage_data = entry_data.get("storage_data", {})
            medications = storage_data.get("medications", {})
            if med_id in medications:
                remaining_amount = medications[med_id].get("remaining_amount", 0)

        # Base schema
        schema_dict = {
            vol.Required(
                CONF_MEDICATION_NAME,
                default=current_data.get(CONF_MEDICATION_NAME, ""),
            ): str,
            vol.Required(CONF_DOSAGE, default=current_data.get(CONF_DOSAGE, "1")): str,
            vol.Required(
                CONF_MEDICATION_TYPE,
                default=current_data.get(CONF_MEDICATION_TYPE, DEFAULT_MEDICATION_TYPE),
            ): SELECT_MEDICATION_TYPE,
            vol.Optional(
                CONF_STRENGTH,
                default=current_data.get(CONF_STRENGTH, DEFAULT_STRENGTH),
            ): str,
            vol.Required(
                CONF_DOSAGE_UNIT,
                default=current_data.get(CONF_DOSAGE_UNIT, DEFAULT_DOSAGE_UNIT),
            ): SELECT_DOSAGE_UNIT,
            vol.Required(
                CONF_CURRENT_QUANTITY,
                default=remaining_amount,
            ): vol.Coerce(int),
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
                {"entity": {}}  # Allow all entity types
            )

            # Add trigger value and duplicate avoidance options
            sensor_entity_id = current_data.get(CONF_RELATIVE_TO_SENSOR)
            if sensor_entity_id:
                sensor_state = self.hass.states.get(sensor_entity_id)
                if sensor_state:
                    sensor_type = self._detect_sensor_type(sensor_state)
                    trigger_value_options = self._get_trigger_value_options(
                        sensor_state, sensor_type
                    )

                    if trigger_value_options:
                        schema_dict[
                            vol.Optional(
                                CONF_SENSOR_TRIGGER_VALUE,
                                default=current_data.get(
                                    CONF_SENSOR_TRIGGER_VALUE,
                                    DEFAULT_SENSOR_TRIGGER_VALUE,
                                ),
                            )
                        ] = selector(
                            {
                                "select": {
                                    "options": trigger_value_options,
                                    "mode": "dropdown",
                                    "custom_value": True,
                                }
                            }
                        )
                    else:
                        schema_dict[
                            vol.Optional(
                                CONF_SENSOR_TRIGGER_VALUE,
                                default=current_data.get(
                                    CONF_SENSOR_TRIGGER_VALUE,
                                    DEFAULT_SENSOR_TRIGGER_VALUE,
                                ),
                            )
                        ] = selector({"text": {}})

                    # Add attribute selector if entity has attributes
                    if sensor_state.attributes:
                        available_attrs = [
                            {"label": "State (default)", "value": ""},
                        ]
                        for attr_name in sensor_state.attributes.keys():
                            if attr_name not in [
                                "friendly_name",
                                "icon",
                                "device_class",
                                "unit_of_measurement",
                            ]:
                                available_attrs.append(
                                    {"label": attr_name, "value": attr_name}
                                )

                        if len(available_attrs) > 1:
                            schema_dict[
                                vol.Optional(
                                    CONF_SENSOR_TRIGGER_ATTRIBUTE,
                                    default=current_data.get(
                                        CONF_SENSOR_TRIGGER_ATTRIBUTE,
                                        DEFAULT_SENSOR_TRIGGER_ATTRIBUTE,
                                    ),
                                )
                            ] = selector(
                                {
                                    "select": {
                                        "options": available_attrs,
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
            schema_dict[
                vol.Optional(
                    CONF_AVOID_DUPLICATE_TRIGGERS,
                    default=current_data.get(
                        CONF_AVOID_DUPLICATE_TRIGGERS, DEFAULT_AVOID_DUPLICATE_TRIGGERS
                    ),
                )
            ] = selector({"boolean": {}})
            schema_dict[
                vol.Optional(
                    CONF_IGNORE_UNAVAILABLE,
                    default=current_data.get(
                        CONF_IGNORE_UNAVAILABLE, DEFAULT_IGNORE_UNAVAILABLE
                    ),
                )
            ] = selector({"boolean": {}})

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
            vol.Optional(
                CONF_ENABLE_AUTOMATIC_NOTIFICATIONS,
                default=current_data.get(
                    CONF_ENABLE_AUTOMATIC_NOTIFICATIONS,
                    DEFAULT_ENABLE_AUTOMATIC_NOTIFICATIONS,
                ),
            )
        ] = selector({"boolean": {}})
        schema_dict[
            vol.Optional(
                CONF_ON_TIME_WINDOW_MINUTES,
                default=current_data.get(
                    CONF_ON_TIME_WINDOW_MINUTES, DEFAULT_ON_TIME_WINDOW_MINUTES
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
            errors=errors,
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
            self._temp_user_input[CONF_SCHEDULE_TIMES] = (
                existing_times + clarified_times
            )
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

    def _detect_sensor_type(self, sensor_state):
        """Detect the type of sensor based on its attributes and state."""
        if not sensor_state:
            return "unknown"

        domain = sensor_state.entity_id.split(".")[0]

        # Binary sensors have on/off states
        if domain == "binary_sensor":
            return "binary"

        # Check attributes for sensor class
        attributes = sensor_state.attributes
        device_class = attributes.get("device_class")
        unit = attributes.get("unit_of_measurement")

        if device_class:
            return device_class

        # Try to detect from state value
        state_value = sensor_state.state

        # Check if numeric
        try:
            float(state_value)
            return "numeric"
        except (ValueError, TypeError):
            pass

        # Check common state patterns
        if state_value in ["on", "off", "true", "false", "open", "closed"]:
            return "binary_like"

        return "text"

    def _get_trigger_value_options(self, sensor_state, sensor_type):
        """Get appropriate trigger value options based on sensor type."""
        if not sensor_state:
            return []

        options = []

        if sensor_type == "binary" or sensor_type == "binary_like":
            # Binary sensors or sensors with binary-like values
            current_state = sensor_state.state.lower() if sensor_state.state else ""
            if current_state in ["on", "off"]:
                options = [
                    {"label": "On", "value": "on"},
                    {"label": "Off", "value": "off"},
                ]
            elif current_state in ["true", "false"]:
                options = [
                    {"label": "True", "value": "true"},
                    {"label": "False", "value": "false"},
                ]
            elif current_state in ["open", "closed"]:
                options = [
                    {"label": "Open", "value": "open"},
                    {"label": "Closed", "value": "closed"},
                ]
            else:
                # Provide both on and off as defaults
                options = [
                    {"label": "On", "value": "on"},
                    {"label": "Off", "value": "off"},
                ]
        elif sensor_type == "numeric":
            # For numeric sensors, user can enter custom values
            # Return empty to show text input
            return []
        else:
            # For other sensors, get unique values from history or use text input
            return []

        # Add "Any change" option at the beginning
        options.insert(0, {"label": "Any change (empty)", "value": ""})

        return options
