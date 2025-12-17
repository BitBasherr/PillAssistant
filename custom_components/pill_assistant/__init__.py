"""Pill Assistant integration for Home Assistant."""

from __future__ import annotations

import logging
from datetime import timedelta
import os

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN,
    STORAGE_VERSION,
    STORAGE_KEY,
    LOG_FILE_NAME,
    SERVICE_TAKE_MEDICATION,
    SERVICE_SKIP_MEDICATION,
    SERVICE_REFILL_MEDICATION,
    SERVICE_TEST_NOTIFICATION,
    SERVICE_SNOOZE_MEDICATION,
    SERVICE_INCREMENT_DOSAGE,
    SERVICE_DECREMENT_DOSAGE,
    ATTR_MEDICATION_ID,
    ATTR_SNOOZE_DURATION,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_REFILL_AMOUNT,
    CONF_NOTIFY_SERVICES,
    DEFAULT_SNOOZE_DURATION_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

# Service schemas for validation
SERVICE_TAKE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

SERVICE_SKIP_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

SERVICE_REFILL_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

SERVICE_TEST_NOTIFICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

SERVICE_SNOOZE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
        vol.Optional(ATTR_SNOOZE_DURATION): vol.Coerce(int),
    }
)

SERVICE_INCREMENT_DOSAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

SERVICE_DECREMENT_DOSAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Pill Assistant component."""
    hass.data.setdefault(DOMAIN, {})
    
    # Register the www directory with the http component for static file serving
    # Only register if http component is available (not in test environment)
    if not hass.data[DOMAIN].get("panel_registered") and hass.http is not None:
        www_path = os.path.join(os.path.dirname(__file__), "www")
        hass.http.register_static_path(
            f"/{DOMAIN}",
            www_path,
            cache_headers=False,
        )
        hass.data[DOMAIN]["panel_registered"] = True
        _LOGGER.info("Pill Assistant panel available at /%s/pill-assistant-panel.html", DOMAIN)
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pill Assistant from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize storage
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    storage_data = await store.async_load() or {}

    if "medications" not in storage_data:
        storage_data["medications"] = {}

    if "history" not in storage_data:
        storage_data["history"] = []

    # Store the entry data in storage if not already there
    med_id = entry.entry_id
    if med_id not in storage_data["medications"]:
        storage_data["medications"][med_id] = {
            **entry.data,
            "remaining_amount": entry.data.get(CONF_REFILL_AMOUNT, 0),
            "last_taken": None,
            "missed_doses": [],
        }
        await store.async_save(storage_data)

    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "store": store,
        "storage_data": storage_data,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register event listener for notification actions
    async def handle_notification_action(event):
        """Handle notification action events from mobile_app."""
        action = event.data.get("action")
        if not action:
            return

        # Parse the action to extract medication ID
        if action.startswith("take_medication_"):
            med_id = action.replace("take_medication_", "")
            if med_id in hass.data[DOMAIN]:
                await hass.services.async_call(
                    DOMAIN,
                    SERVICE_TAKE_MEDICATION,
                    {ATTR_MEDICATION_ID: med_id},
                    blocking=True,
                )
                _LOGGER.info("Medication %s marked as taken via notification action", med_id)
        elif action.startswith("snooze_medication_"):
            med_id = action.replace("snooze_medication_", "")
            if med_id in hass.data[DOMAIN]:
                await hass.services.async_call(
                    DOMAIN,
                    SERVICE_SNOOZE_MEDICATION,
                    {ATTR_MEDICATION_ID: med_id},
                    blocking=True,
                )
                _LOGGER.info("Medication %s snoozed via notification action", med_id)
        elif action.startswith("skip_medication_"):
            med_id = action.replace("skip_medication_", "")
            if med_id in hass.data[DOMAIN]:
                await hass.services.async_call(
                    DOMAIN,
                    SERVICE_SKIP_MEDICATION,
                    {ATTR_MEDICATION_ID: med_id},
                    blocking=True,
                )
                _LOGGER.info("Medication %s skipped via notification action", med_id)

    # Listen for mobile_app notification action events
    hass.bus.async_listen("mobile_app_notification_action", handle_notification_action)
    # Also listen for ios.notification_action_fired for iOS devices
    hass.bus.async_listen("ios.notification_action_fired", handle_notification_action)

    # Register services
    async def handle_take_medication(call: ServiceCall) -> None:
        """Handle take medication service."""
        med_id = call.data.get(ATTR_MEDICATION_ID)
        if med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", med_id)
            return

        entry_data = hass.data[DOMAIN][med_id]
        store = entry_data["store"]
        storage_data = entry_data["storage_data"]

        med_data = storage_data["medications"].get(med_id)
        if not med_data:
            _LOGGER.error("Medication data for %s not found", med_id)
            return

        # Update last taken time
        now = dt_util.now()
        med_data["last_taken"] = now.isoformat()

        # Decrease remaining amount by 1 dose (not by dosage amount)
        remaining = float(med_data.get("remaining_amount", 0))
        med_data["remaining_amount"] = max(0, remaining - 1)

        # Add to history
        history_entry = {
            "medication_id": med_id,
            "medication_name": med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            "timestamp": now.isoformat(),
            "action": "taken",
            "dosage": med_data.get(CONF_DOSAGE, ""),
            "dosage_unit": med_data.get(CONF_DOSAGE_UNIT, ""),
        }
        storage_data["history"].append(history_entry)

        # Save to storage
        await store.async_save(storage_data)

        # Append to persistent log file
        log_path = hass.config.path(LOG_FILE_NAME)
        log_line = f"{now.strftime('%Y-%m-%d %H:%M:%S')} - TAKEN - {med_data.get(CONF_MEDICATION_NAME, 'Unknown')} - {med_data.get(CONF_DOSAGE, '')} {med_data.get(CONF_DOSAGE_UNIT, '')}\n"
        try:
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(log_line)
        except Exception as e:
            _LOGGER.error("Failed to write to log file: %s", e)

        _LOGGER.info(
            "Medication %s taken at %s", med_data.get(CONF_MEDICATION_NAME), now
        )

    async def handle_skip_medication(call: ServiceCall) -> None:
        """Handle skip medication service."""
        med_id = call.data.get(ATTR_MEDICATION_ID)
        if med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", med_id)
            return

        entry_data = hass.data[DOMAIN][med_id]
        store = entry_data["store"]
        storage_data = entry_data["storage_data"]

        med_data = storage_data["medications"].get(med_id)
        if not med_data:
            return

        now = dt_util.now()

        # Add to history
        history_entry = {
            "medication_id": med_id,
            "medication_name": med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            "timestamp": now.isoformat(),
            "action": "skipped",
        }
        storage_data["history"].append(history_entry)

        await store.async_save(storage_data)

        # Append to persistent log file
        log_path = hass.config.path(LOG_FILE_NAME)
        log_line = f"{now.strftime('%Y-%m-%d %H:%M:%S')} - SKIPPED - {med_data.get(CONF_MEDICATION_NAME, 'Unknown')}\n"
        try:
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(log_line)
        except Exception as e:
            _LOGGER.error("Failed to write to log file: %s", e)

        _LOGGER.info(
            "Medication %s skipped at %s", med_data.get(CONF_MEDICATION_NAME), now
        )

    async def handle_refill_medication(call: ServiceCall) -> None:
        """Handle refill medication service."""
        med_id = call.data.get(ATTR_MEDICATION_ID)
        if med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", med_id)
            return

        entry_data = hass.data[DOMAIN][med_id]
        store = entry_data["store"]
        storage_data = entry_data["storage_data"]

        med_data = storage_data["medications"].get(med_id)
        if not med_data:
            return

        # Reset to full refill amount
        refill_amount = med_data.get(CONF_REFILL_AMOUNT, 0)
        med_data["remaining_amount"] = refill_amount

        now = dt_util.now()

        # Add to history
        history_entry = {
            "medication_id": med_id,
            "medication_name": med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            "timestamp": now.isoformat(),
            "action": "refilled",
            "amount": refill_amount,
        }
        storage_data["history"].append(history_entry)

        await store.async_save(storage_data)

        # Append to persistent log file
        log_path = hass.config.path(LOG_FILE_NAME)
        log_line = f"{now.strftime('%Y-%m-%d %H:%M:%S')} - REFILLED - {med_data.get(CONF_MEDICATION_NAME, 'Unknown')} - {refill_amount} units\n"
        try:
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(log_line)
        except Exception as e:
            _LOGGER.error("Failed to write to log file: %s", e)

        _LOGGER.info(
            "Medication %s refilled to %s at %s",
            med_data.get(CONF_MEDICATION_NAME),
            refill_amount,
            now,
        )

    async def handle_test_notification(call: ServiceCall) -> None:
        """Handle test notification service."""
        med_id = call.data.get(ATTR_MEDICATION_ID)
        if med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", med_id)
            return

        entry_data = hass.data[DOMAIN][med_id]
        storage_data = entry_data["storage_data"]

        med_data = storage_data["medications"].get(med_id)
        if not med_data:
            return

        # Get medication details
        med_name = med_data.get(CONF_MEDICATION_NAME, "Unknown")
        dosage = med_data.get(CONF_DOSAGE, "")
        dosage_unit = med_data.get(CONF_DOSAGE_UNIT, "")
        notify_services = med_data.get(CONF_NOTIFY_SERVICES, [])

        # Create notification message
        message = (
            f"Test notification: Time to take {dosage} {dosage_unit} of {med_name}"
        )
        title = "Medication Reminder (Test)"

        # Send notification to configured services
        if notify_services:
            for service_name in notify_services:
                try:
                    # Extract domain and service
                    service_parts = service_name.split(".")
                    if len(service_parts) == 2:
                        domain, service = service_parts
                        await hass.services.async_call(
                            domain,
                            service,
                            {
                                "title": title,
                                "message": message,
                                "data": {
                                    "tag": f"pill_assistant_{med_id}",
                                    "actions": [
                                        {
                                            "action": f"take_medication_{med_id}",
                                            "title": "Mark as Taken",
                                        },
                                        {
                                            "action": f"snooze_medication_{med_id}",
                                            "title": "Snooze",
                                        },
                                        {
                                            "action": f"skip_medication_{med_id}",
                                            "title": "Skip",
                                        },
                                    ],
                                },
                            },
                            blocking=False,
                        )
                except Exception as e:
                    _LOGGER.error(
                        "Failed to send notification via %s: %s", service_name, e
                    )
        else:
            # Fall back to persistent notification
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"pill_assistant_test_{med_id}",
                },
                blocking=False,
            )

        _LOGGER.info("Test notification sent for %s", med_name)

    async def handle_snooze_medication(call: ServiceCall) -> None:
        """Handle snooze medication service."""
        med_id = call.data.get(ATTR_MEDICATION_ID)
        snooze_duration = call.data.get(
            ATTR_SNOOZE_DURATION, DEFAULT_SNOOZE_DURATION_MINUTES
        )

        if med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", med_id)
            return

        entry_data = hass.data[DOMAIN][med_id]
        store = entry_data["store"]
        storage_data = entry_data["storage_data"]

        med_data = storage_data["medications"].get(med_id)
        if not med_data:
            return

        # Calculate snooze until time
        now = dt_util.now()
        snooze_until = now + timedelta(minutes=int(snooze_duration))

        # Store snooze information
        med_data["snooze_until"] = snooze_until.isoformat()

        await store.async_save(storage_data)

        _LOGGER.info(
            "Medication %s snoozed for %s minutes until %s",
            med_data.get(CONF_MEDICATION_NAME),
            snooze_duration,
            snooze_until,
        )

    async def handle_increment_dosage(call: ServiceCall) -> None:
        """Handle increment dosage service."""
        med_id = call.data.get(ATTR_MEDICATION_ID)
        if med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", med_id)
            return

        entry_data = hass.data[DOMAIN][med_id]
        store = entry_data["store"]
        storage_data = entry_data["storage_data"]

        med_data = storage_data["medications"].get(med_id)
        if not med_data:
            return

        # Increment dosage by 0.5 (works for pills, tablets, etc.)
        current_dosage = float(med_data.get(CONF_DOSAGE, 1))
        new_dosage = current_dosage + 0.5
        med_data[CONF_DOSAGE] = str(new_dosage)

        await store.async_save(storage_data)

        _LOGGER.info(
            "Medication %s dosage incremented from %s to %s",
            med_data.get(CONF_MEDICATION_NAME),
            current_dosage,
            new_dosage,
        )

    async def handle_decrement_dosage(call: ServiceCall) -> None:
        """Handle decrement dosage service."""
        med_id = call.data.get(ATTR_MEDICATION_ID)
        if med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", med_id)
            return

        entry_data = hass.data[DOMAIN][med_id]
        store = entry_data["store"]
        storage_data = entry_data["storage_data"]

        med_data = storage_data["medications"].get(med_id)
        if not med_data:
            return

        # Decrement dosage by 0.5 (works for pills, tablets, etc.), minimum 0.5
        current_dosage = float(med_data.get(CONF_DOSAGE, 1))
        new_dosage = max(0.5, current_dosage - 0.5)
        med_data[CONF_DOSAGE] = str(new_dosage)

        await store.async_save(storage_data)

        _LOGGER.info(
            "Medication %s dosage decremented from %s to %s",
            med_data.get(CONF_MEDICATION_NAME),
            current_dosage,
            new_dosage,
        )

    # Register services only once
    if not hass.services.has_service(DOMAIN, SERVICE_TAKE_MEDICATION):
        hass.services.async_register(
            DOMAIN,
            SERVICE_TAKE_MEDICATION,
            handle_take_medication,
            schema=SERVICE_TAKE_MEDICATION_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SKIP_MEDICATION):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SKIP_MEDICATION,
            handle_skip_medication,
            schema=SERVICE_SKIP_MEDICATION_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_REFILL_MEDICATION):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFILL_MEDICATION,
            handle_refill_medication,
            schema=SERVICE_REFILL_MEDICATION_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_TEST_NOTIFICATION):
        hass.services.async_register(
            DOMAIN,
            SERVICE_TEST_NOTIFICATION,
            handle_test_notification,
            schema=SERVICE_TEST_NOTIFICATION_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SNOOZE_MEDICATION):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SNOOZE_MEDICATION,
            handle_snooze_medication,
            schema=SERVICE_SNOOZE_MEDICATION_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_INCREMENT_DOSAGE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_INCREMENT_DOSAGE,
            handle_increment_dosage,
            schema=SERVICE_INCREMENT_DOSAGE_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_DECREMENT_DOSAGE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DECREMENT_DOSAGE,
            handle_decrement_dosage,
            schema=SERVICE_DECREMENT_DOSAGE_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
