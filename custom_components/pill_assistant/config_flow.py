"""Config flow for Pill Assistant."""

from __future__ import annotations

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
    CONF_CREATE_TEST_BUTTON,
    CONF_SNOOZE_DURATION_MINUTES,
    DEFAULT_DOSAGE_UNIT,
    DEFAULT_REFILL_REMINDER_DAYS,
    DEFAULT_SCHEDULE_DAYS,
    DEFAULT_SCHEDULE_TYPE,
    DEFAULT_CREATE_TEST_BUTTON,
    DEFAULT_SNOOZE_DURATION_MINUTES,
    DEFAULT_RELATIVE_OFFSET_HOURS,
    DEFAULT_RELATIVE_OFFSET_MINUTES,
    SCHEDULE_TYPE_OPTIONS,
    SELECT_DOSAGE_UNIT,
    SELECT_DAYS,
    SELECT_TIME,
)


class PillAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pill Assistant."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}

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
            user_input[CONF_SCHEDULE_TIMES] = schedule_times

            # Ensure schedule_days is set
            if not user_input.get(CONF_SCHEDULE_DAYS):
                user_input[CONF_SCHEDULE_DAYS] = DEFAULT_SCHEDULE_DAYS

            self._data.update(user_input)
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
                "schedule_times_example": "Enter times in HH:MM format (e.g., 08:00, 20:00)"
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
                existing_meds.append({
                    "label": med_name,
                    "value": entry.entry_id
                })

        schema_dict = {
            vol.Required(CONF_RELATIVE_OFFSET_HOURS, default=DEFAULT_RELATIVE_OFFSET_HOURS): vol.Coerce(int),
            vol.Required(CONF_RELATIVE_OFFSET_MINUTES, default=DEFAULT_RELATIVE_OFFSET_MINUTES): vol.Coerce(int),
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
                    vol.Required(CONF_RELATIVE_OFFSET_HOURS, default=DEFAULT_RELATIVE_OFFSET_HOURS): vol.Coerce(int),
                    vol.Required(CONF_RELATIVE_OFFSET_MINUTES, default=DEFAULT_RELATIVE_OFFSET_MINUTES): vol.Coerce(int),
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

            # Create the entry first
            entry = self.async_create_entry(
                title=self._data[CONF_MEDICATION_NAME],
                data=self._data,
            )
            
            # If requested, create input_button helper for test notifications
            if user_input.get(CONF_CREATE_TEST_BUTTON, DEFAULT_CREATE_TEST_BUTTON):
                try:
                    await self._create_test_button(self._data[CONF_MEDICATION_NAME])
                except Exception as e:
                    # Log error but don't fail the entire setup
                    import logging
                    _LOGGER = logging.getLogger(__name__)
                    _LOGGER.warning("Failed to create test button: %s", e)
            
            return entry

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
            vol.Optional(
                CONF_CREATE_TEST_BUTTON, default=DEFAULT_CREATE_TEST_BUTTON
            ): bool,
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

    async def _create_test_button(self, medication_name: str) -> None:
        """Create an input_button helper for test notifications."""
        # Sanitize medication name for entity_id
        button_name = f"test_{medication_name.lower().replace(' ', '_')}_notification"
        
        # Create input_button using the input_button service
        await self.hass.services.async_call(
            "input_button",
            "create",
            {
                "name": f"Test {medication_name} Notification",
            },
            blocking=True,
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
            # Update the config entry with new data
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={**self._config_entry.data, **user_input},
            )
            
            # If requested, create input_button helper for test notifications
            if user_input.get(CONF_CREATE_TEST_BUTTON, False):
                try:
                    await self._create_test_button(user_input[CONF_MEDICATION_NAME])
                except Exception as e:
                    # Log error but don't fail the entire update
                    import logging
                    _LOGGER = logging.getLogger(__name__)
                    _LOGGER.warning("Failed to create test button: %s", e)
            
            return self.async_create_entry(title="", data={})

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
            schema_dict[vol.Required(
                CONF_SCHEDULE_TIMES,
                default=current_data.get(CONF_SCHEDULE_TIMES, []),
            )] = selector(
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
                    existing_meds.append({
                        "label": med_name,
                        "value": entry.entry_id
                    })
            
            if existing_meds:
                schema_dict[vol.Required(
                    CONF_RELATIVE_TO_MEDICATION,
                    default=current_data.get(CONF_RELATIVE_TO_MEDICATION, existing_meds[0]["value"] if existing_meds else ""),
                )] = selector(
                    {
                        "select": {
                            "options": existing_meds,
                            "mode": "dropdown",
                        }
                    }
                )
            
            schema_dict[vol.Required(
                CONF_RELATIVE_OFFSET_HOURS,
                default=current_data.get(CONF_RELATIVE_OFFSET_HOURS, DEFAULT_RELATIVE_OFFSET_HOURS),
            )] = vol.Coerce(int)
            schema_dict[vol.Required(
                CONF_RELATIVE_OFFSET_MINUTES,
                default=current_data.get(CONF_RELATIVE_OFFSET_MINUTES, DEFAULT_RELATIVE_OFFSET_MINUTES),
            )] = vol.Coerce(int)
        elif schedule_type == "relative_sensor":
            schema_dict[vol.Required(
                CONF_RELATIVE_TO_SENSOR,
                default=current_data.get(CONF_RELATIVE_TO_SENSOR, ""),
            )] = selector(
                {
                    "entity": {
                        "domain": ["binary_sensor", "sensor"],
                    }
                }
            )
            schema_dict[vol.Required(
                CONF_RELATIVE_OFFSET_HOURS,
                default=current_data.get(CONF_RELATIVE_OFFSET_HOURS, DEFAULT_RELATIVE_OFFSET_HOURS),
            )] = vol.Coerce(int)
            schema_dict[vol.Required(
                CONF_RELATIVE_OFFSET_MINUTES,
                default=current_data.get(CONF_RELATIVE_OFFSET_MINUTES, DEFAULT_RELATIVE_OFFSET_MINUTES),
            )] = vol.Coerce(int)

        # Add common fields
        schema_dict[vol.Required(
            CONF_SCHEDULE_DAYS,
            default=current_data.get(CONF_SCHEDULE_DAYS, DEFAULT_SCHEDULE_DAYS),
        )] = SELECT_DAYS
        schema_dict[vol.Required(
            CONF_REFILL_AMOUNT,
            default=current_data.get(CONF_REFILL_AMOUNT, 30),
        )] = vol.Coerce(int)
        schema_dict[vol.Required(
            CONF_REFILL_REMINDER_DAYS,
            default=current_data.get(
                CONF_REFILL_REMINDER_DAYS, DEFAULT_REFILL_REMINDER_DAYS
            ),
        )] = vol.Coerce(int)
        schema_dict[vol.Optional(
            CONF_SNOOZE_DURATION_MINUTES,
            default=current_data.get(CONF_SNOOZE_DURATION_MINUTES, DEFAULT_SNOOZE_DURATION_MINUTES),
        )] = vol.Coerce(int)
        schema_dict[vol.Optional(CONF_NOTES, default=current_data.get(CONF_NOTES, ""))] = str
        schema_dict[vol.Optional(CONF_CREATE_TEST_BUTTON, default=False)] = bool

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

    async def _create_test_button(self, medication_name: str) -> None:
        """Create an input_button helper for test notifications."""
        # Sanitize medication name for entity_id
        button_name = f"test_{medication_name.lower().replace(' ', '_')}_notification"
        
        # Create input_button using the input_button service
        await self.hass.services.async_call(
            "input_button",
            "create",
            {
                "name": f"Test {medication_name} Notification",
            },
            blocking=True,
        )
