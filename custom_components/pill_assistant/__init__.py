"""Pill Assistant integration for Home Assistant."""

from __future__ import annotations

import logging
import os
from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
import homeassistant.util.dt as dt_util

try:  # HA version compatibility: StaticPathConfig may not exist in tests
    from homeassistant.components.http import StaticPathConfig
except ImportError:  # pragma: no cover - older HA / test env without StaticPathConfig
    StaticPathConfig = None  # type: ignore[assignment]

from .const import (
    ATTR_MEDICATION_ID,
    ATTR_SNOOZE_DURATION,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_MEDICATION_NAME,
    CONF_NOTIFY_SERVICES,
    CONF_REFILL_AMOUNT,
    DEFAULT_SNOOZE_DURATION_MINUTES,
    DOMAIN,
    LOG_FILE_NAME,
    SERVICE_DECREMENT_DOSAGE,
    SERVICE_DECREMENT_REMAINING,
    SERVICE_INCREMENT_DOSAGE,
    SERVICE_INCREMENT_REMAINING,
    SERVICE_REFILL_MEDICATION,
    SERVICE_SKIP_MEDICATION,
    SERVICE_SNOOZE_MEDICATION,
    SERVICE_TAKE_MEDICATION,
    SERVICE_TEST_NOTIFICATION,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from . import log_utils

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

# Dispatcher signal for sensor updates
SIGNAL_MEDICATION_UPDATED = f"{DOMAIN}_medication_updated"

# Service schemas for validation
SERVICE_TAKE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    },
)

SERVICE_SKIP_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    },
)

SERVICE_REFILL_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    },
)

SERVICE_TEST_NOTIFICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    },
)

SERVICE_SNOOZE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
        vol.Optional(ATTR_SNOOZE_DURATION): vol.Coerce(int),
    },
)

SERVICE_INCREMENT_DOSAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    },
)

SERVICE_DECREMENT_DOSAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    },
)

SERVICE_INCREMENT_REMAINING_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    },
)

SERVICE_DECREMENT_REMAINING_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    },
)


async def _register_panel_static_path(hass: HomeAssistant) -> None:
    """Register static path for the Pill Assistant panel.

    This is written to be compatible with multiple HA versions:
    - New API: async_register_static_paths([StaticPathConfig(...), ...])
    - Older API: async_register_static_paths(path, directory)
    - Fallback:  register_static_path(path, directory)
    """
    if getattr(hass, "http", None) is None:
        return

    www_path = os.path.join(os.path.dirname(__file__), "www")
    base_path = f"/{DOMAIN}"

    # Preferred: new-style API with StaticPathConfig
    if StaticPathConfig is not None and hasattr(
        hass.http,
        "async_register_static_paths",
    ):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    base_path,
                    www_path,
                    False,
                ),
            ],
        )
        return

    # Fallback: older async_register_static_paths(path, directory)
    if hasattr(hass.http, "async_register_static_paths"):
        result = hass.http.async_register_static_paths(
            base_path,
            www_path,
        )
        # If this returned a coroutine/awaitable, await it; otherwise just return
        if hasattr(result, "__await__"):
            await result
        return

    # Last resort: very old sync register_static_path(path, directory)
    if hasattr(hass.http, "register_static_path"):
        hass.http.register_static_path(
            base_path,
            www_path,
        )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Pill Assistant component."""
    hass.data.setdefault(DOMAIN, {})

    # Ensure logs directory exists
    def ensure_logs_dir():
        logs_dir = log_utils.get_logs_dir(hass)
        os.makedirs(logs_dir, exist_ok=True)

    await hass.async_add_executor_job(ensure_logs_dir)

    # Register the www directory with the http component for static file serving
    # Only register if http component is available (not in test environment)
    if not hass.data[DOMAIN].get("panel_registered") and getattr(
        hass,
        "http",
        None,
    ):
        await _register_panel_static_path(hass)
        hass.data[DOMAIN]["panel_registered"] = True
        _LOGGER.info(
            "Pill Assistant panel available at /%s/pill-assistant-panel.html",
            DOMAIN,
        )

    # Register sidebar iframe panel automatically
    if not hass.data[DOMAIN].get("sidebar_registered"):
        try:
            # Use HA frontend component to register iframe panel
            # Import the frontend component dynamically to avoid issues
            if "frontend" in hass.config.components:
                from homeassistant.components import frontend

                # Note: Despite the name, async_register_built_in_panel is a regular
                # function decorated with @callback, not an async function, so no await
                frontend.async_register_built_in_panel(
                    hass,
                    "iframe",
                    "Pill Assistant",
                    "mdi:pill",
                    DOMAIN,
                    f"/{DOMAIN}/pill-assistant-panel.html",
                    require_admin=True,
                )
                hass.data[DOMAIN]["sidebar_registered"] = True
                _LOGGER.info("Pill Assistant sidebar panel registered")
        except Exception as err:  # pragma: no cover - panel registration failure
            _LOGGER.warning("Failed to register sidebar panel: %s", err)

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
    async def handle_notification_action(event) -> None:
        """Handle notification action events from mobile_app."""
        action = event.data.get("action")
        if not action:
            return

        # Parse the action to extract medication ID
        if action.startswith("take_medication_"):
            _med_id = action.replace("take_medication_", "")
            if _med_id in hass.data[DOMAIN]:
                await hass.services.async_call(
                    DOMAIN,
                    SERVICE_TAKE_MEDICATION,
                    {ATTR_MEDICATION_ID: _med_id},
                    blocking=True,
                )
                _LOGGER.info(
                    "Medication %s marked as taken via notification action",
                    _med_id,
                )
        elif action.startswith("snooze_medication_"):
            _med_id = action.replace("snooze_medication_", "")
            if _med_id in hass.data[DOMAIN]:
                await hass.services.async_call(
                    DOMAIN,
                    SERVICE_SNOOZE_MEDICATION,
                    {ATTR_MEDICATION_ID: _med_id},
                    blocking=True,
                )
                _LOGGER.info(
                    "Medication %s snoozed via notification action",
                    _med_id,
                )
        elif action.startswith("skip_medication_"):
            _med_id = action.replace("skip_medication_", "")
            if _med_id in hass.data[DOMAIN]:
                await hass.services.async_call(
                    DOMAIN,
                    SERVICE_SKIP_MEDICATION,
                    {ATTR_MEDICATION_ID: _med_id},
                    blocking=True,
                )
                _LOGGER.info(
                    "Medication %s skipped via notification action",
                    _med_id,
                )

    # Listen for mobile_app notification action events
    hass.bus.async_listen(
        "mobile_app_notification_action",
        handle_notification_action,
    )
    # Also listen for ios.notification_action_fired for iOS devices
    hass.bus.async_listen(
        "ios.notification_action_fired",
        handle_notification_action,
    )

    # Register services
    async def handle_take_medication(call: ServiceCall) -> None:
        """Handle take medication service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data = hass.data[DOMAIN][_med_id]
        _store = entry_data["store"]
        _storage_data = entry_data["storage_data"]

        med_data = _storage_data["medications"].get(_med_id)
        if not med_data:
            _LOGGER.error("Medication data for %s not found", _med_id)
            return

        # Update last taken time
        now = dt_util.now()
        med_data["last_taken"] = now.isoformat()

        # Decrease remaining amount by 1 dose (not by dosage amount)
        remaining = float(med_data.get("remaining_amount", 0))
        med_data["remaining_amount"] = max(0, remaining - 1)

        # Add to history
        history_entry = {
            "medication_id": _med_id,
            "medication_name": med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            "timestamp": now.isoformat(),
            "action": "taken",
            "dosage": med_data.get(CONF_DOSAGE, ""),
            "dosage_unit": med_data.get(CONF_DOSAGE_UNIT, ""),
        }
        _storage_data["history"].append(history_entry)

        # Save to storage
        await _store.async_save(_storage_data)

        # Write to CSV log files
        await log_utils.async_log_event(
            hass,
            action="taken",
            medication_id=_med_id,
            medication_name=med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            dosage=med_data.get(CONF_DOSAGE),
            dosage_unit=med_data.get(CONF_DOSAGE_UNIT),
            remaining_amount=med_data.get("remaining_amount"),
            refill_amount=med_data.get(CONF_REFILL_AMOUNT),
            snooze_until=None,
            details={"timestamp": now.isoformat()},
        )

        # Fire dispatcher signal for immediate sensor update
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")

        _LOGGER.info(
            "Medication %s taken at %s",
            med_data.get(CONF_MEDICATION_NAME),
            now,
        )

    async def handle_skip_medication(call: ServiceCall) -> None:
        """Handle skip medication service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data = hass.data[DOMAIN][_med_id]
        _store = entry_data["store"]
        _storage_data = entry_data["storage_data"]

        med_data = _storage_data["medications"].get(_med_id)
        if not med_data:
            return

        now = dt_util.now()

        # Add to history
        history_entry = {
            "medication_id": _med_id,
            "medication_name": med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            "timestamp": now.isoformat(),
            "action": "skipped",
        }
        _storage_data["history"].append(history_entry)

        await _store.async_save(_storage_data)

        # Write to CSV log files
        await log_utils.async_log_event(
            hass,
            action="skipped",
            medication_id=_med_id,
            medication_name=med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            dosage=med_data.get(CONF_DOSAGE),
            dosage_unit=med_data.get(CONF_DOSAGE_UNIT),
            remaining_amount=med_data.get("remaining_amount"),
            refill_amount=med_data.get(CONF_REFILL_AMOUNT),
            snooze_until=None,
            details={"timestamp": now.isoformat()},
        )

        # Fire dispatcher signal for immediate sensor update
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")

        _LOGGER.info(
            "Medication %s skipped at %s",
            med_data.get(CONF_MEDICATION_NAME),
            now,
        )

    async def handle_refill_medication(call: ServiceCall) -> None:
        """Handle refill medication service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data = hass.data[DOMAIN][_med_id]
        _store = entry_data["store"]
        _storage_data = entry_data["storage_data"]

        med_data = _storage_data["medications"].get(_med_id)
        if not med_data:
            return

        # Reset to full refill amount
        refill_amount = med_data.get(CONF_REFILL_AMOUNT, 0)
        med_data["remaining_amount"] = refill_amount

        now = dt_util.now()

        # Add to history
        history_entry = {
            "medication_id": _med_id,
            "medication_name": med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            "timestamp": now.isoformat(),
            "action": "refilled",
            "amount": refill_amount,
        }
        _storage_data["history"].append(history_entry)

        await _store.async_save(_storage_data)

        # Write to CSV log files
        await log_utils.async_log_event(
            hass,
            action="refilled",
            medication_id=_med_id,
            medication_name=med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            dosage=med_data.get(CONF_DOSAGE),
            dosage_unit=med_data.get(CONF_DOSAGE_UNIT),
            remaining_amount=refill_amount,
            refill_amount=refill_amount,
            snooze_until=None,
            details={"timestamp": now.isoformat(), "amount": refill_amount},
        )

        # Fire dispatcher signal for immediate sensor update
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")

        _LOGGER.info(
            "Medication %s refilled to %s at %s",
            med_data.get(CONF_MEDICATION_NAME),
            refill_amount,
            now,
        )

    async def handle_test_notification(call: ServiceCall) -> None:
        """Handle test notification service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data = hass.data[DOMAIN][_med_id]
        _storage_data = entry_data["storage_data"]

        med_data = _storage_data["medications"].get(_med_id)
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
                                    "tag": f"pill_assistant_{_med_id}",
                                    "actions": [
                                        {
                                            "action": f"take_medication_{_med_id}",
                                            "title": "Mark as Taken",
                                        },
                                        {
                                            "action": f"snooze_medication_{_med_id}",
                                            "title": "Snooze",
                                        },
                                        {
                                            "action": f"skip_medication_{_med_id}",
                                            "title": "Skip",
                                        },
                                    ],
                                },
                            },
                            blocking=False,
                        )
                except Exception as err:  # pragma: no cover - notify failure
                    _LOGGER.error(
                        "Failed to send notification via %s: %s",
                        service_name,
                        err,
                    )
        else:
            # Fall back to persistent notification
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"pill_assistant_test_{_med_id}",
                },
                blocking=False,
            )

        _LOGGER.info("Test notification sent for %s", med_name)

    async def handle_snooze_medication(call: ServiceCall) -> None:
        """Handle snooze medication service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        snooze_duration = call.data.get(
            ATTR_SNOOZE_DURATION,
            DEFAULT_SNOOZE_DURATION_MINUTES,
        )

        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data = hass.data[DOMAIN][_med_id]
        _store = entry_data["store"]
        _storage_data = entry_data["storage_data"]

        med_data = _storage_data["medications"].get(_med_id)
        if not med_data:
            return

        # Calculate snooze until time
        now = dt_util.now()
        snooze_until = now + timedelta(minutes=int(snooze_duration))

        # Store snooze information
        med_data["snooze_until"] = snooze_until.isoformat()

        await _store.async_save(_storage_data)

        # Write to CSV log files
        await log_utils.async_log_event(
            hass,
            action="snoozed",
            medication_id=_med_id,
            medication_name=med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            dosage=med_data.get(CONF_DOSAGE),
            dosage_unit=med_data.get(CONF_DOSAGE_UNIT),
            remaining_amount=med_data.get("remaining_amount"),
            refill_amount=med_data.get(CONF_REFILL_AMOUNT),
            snooze_until=snooze_until.isoformat(),
            details={
                "timestamp": now.isoformat(),
                "snooze_duration_minutes": snooze_duration,
            },
        )

        # Fire dispatcher signal for immediate sensor update
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")

        _LOGGER.info(
            "Medication %s snoozed for %s minutes until %s",
            med_data.get(CONF_MEDICATION_NAME),
            snooze_duration,
            snooze_until,
        )

    async def handle_increment_dosage(call: ServiceCall) -> None:
        """Handle increment dosage service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data = hass.data[DOMAIN][_med_id]
        _store = entry_data["store"]
        _storage_data = entry_data["storage_data"]

        med_data = _storage_data["medications"].get(_med_id)
        if not med_data:
            return

        # Increment dosage by 0.5 (works for pills, tablets, etc.)
        current_dosage = float(med_data.get(CONF_DOSAGE, 1))
        new_dosage = current_dosage + 0.5
        med_data[CONF_DOSAGE] = str(new_dosage)

        await _store.async_save(_storage_data)

        # Get timestamp
        now = dt_util.now()

        # Write to CSV log files
        await log_utils.async_log_event(
            hass,
            action="dosage_changed",
            medication_id=_med_id,
            medication_name=med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            dosage=new_dosage,
            dosage_unit=med_data.get(CONF_DOSAGE_UNIT),
            remaining_amount=med_data.get("remaining_amount"),
            refill_amount=med_data.get(CONF_REFILL_AMOUNT),
            snooze_until=None,
            details={
                "timestamp": now.isoformat(),
                "old_dosage": current_dosage,
                "new_dosage": new_dosage,
                "change": "increment",
            },
        )

        # Fire dispatcher signal for immediate sensor update
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")

        _LOGGER.info(
            "Medication %s dosage incremented from %s to %s",
            med_data.get(CONF_MEDICATION_NAME),
            current_dosage,
            new_dosage,
        )

    async def handle_decrement_dosage(call: ServiceCall) -> None:
        """Handle decrement dosage service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data = hass.data[DOMAIN][_med_id]
        _store = entry_data["store"]
        _storage_data = entry_data["storage_data"]

        med_data = _storage_data["medications"].get(_med_id)
        if not med_data:
            return

        # Decrement dosage by 0.5 (works for pills, tablets, etc.), minimum 0.5
        current_dosage = float(med_data.get(CONF_DOSAGE, 1))
        new_dosage = max(0.5, current_dosage - 0.5)
        med_data[CONF_DOSAGE] = str(new_dosage)

        await _store.async_save(_storage_data)

        # Get timestamp
        now = dt_util.now()

        # Write to CSV log files
        await log_utils.async_log_event(
            hass,
            action="dosage_changed",
            medication_id=_med_id,
            medication_name=med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            dosage=new_dosage,
            dosage_unit=med_data.get(CONF_DOSAGE_UNIT),
            remaining_amount=med_data.get("remaining_amount"),
            refill_amount=med_data.get(CONF_REFILL_AMOUNT),
            snooze_until=None,
            details={
                "timestamp": now.isoformat(),
                "old_dosage": current_dosage,
                "new_dosage": new_dosage,
                "change": "decrement",
            },
        )

        # Fire dispatcher signal for immediate sensor update
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")

        _LOGGER.info(
            "Medication %s dosage decremented from %s to %s",
            med_data.get(CONF_MEDICATION_NAME),
            current_dosage,
            new_dosage,
        )

    async def handle_increment_remaining(call: ServiceCall) -> None:
        """Handle increment remaining amount service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data = hass.data[DOMAIN][_med_id]
        _store = entry_data["store"]
        _storage_data = entry_data["storage_data"]

        med_data = _storage_data["medications"].get(_med_id)
        if not med_data:
            return

        # Increment remaining amount by dosage amount
        current_dosage = float(med_data.get(CONF_DOSAGE, 1))
        current_remaining = float(med_data.get("remaining_amount", 0))
        new_remaining = current_remaining + current_dosage
        med_data["remaining_amount"] = new_remaining

        await _store.async_save(_storage_data)

        # Get timestamp
        now = dt_util.now()

        # Write to CSV log files
        await log_utils.async_log_event(
            hass,
            action="remaining_changed",
            medication_id=_med_id,
            medication_name=med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            dosage=med_data.get(CONF_DOSAGE),
            dosage_unit=med_data.get(CONF_DOSAGE_UNIT),
            remaining_amount=new_remaining,
            refill_amount=med_data.get(CONF_REFILL_AMOUNT),
            snooze_until=None,
            details={
                "timestamp": now.isoformat(),
                "old_remaining": current_remaining,
                "new_remaining": new_remaining,
                "change": "increment",
            },
        )

        # Fire dispatcher signal for immediate sensor update
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")

        _LOGGER.info(
            "Medication %s remaining amount incremented from %s to %s",
            med_data.get(CONF_MEDICATION_NAME),
            current_remaining,
            new_remaining,
        )

    async def handle_decrement_remaining(call: ServiceCall) -> None:
        """Handle decrement remaining amount service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data = hass.data[DOMAIN][_med_id]
        _store = entry_data["store"]
        _storage_data = entry_data["storage_data"]

        med_data = _storage_data["medications"].get(_med_id)
        if not med_data:
            return

        # Decrement remaining amount by dosage amount, minimum 0
        current_dosage = float(med_data.get(CONF_DOSAGE, 1))
        current_remaining = float(med_data.get("remaining_amount", 0))
        new_remaining = max(0, current_remaining - current_dosage)
        med_data["remaining_amount"] = new_remaining

        await _store.async_save(_storage_data)

        # Get timestamp
        now = dt_util.now()

        # Write to CSV log files
        await log_utils.async_log_event(
            hass,
            action="remaining_changed",
            medication_id=_med_id,
            medication_name=med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            dosage=med_data.get(CONF_DOSAGE),
            dosage_unit=med_data.get(CONF_DOSAGE_UNIT),
            remaining_amount=new_remaining,
            refill_amount=med_data.get(CONF_REFILL_AMOUNT),
            snooze_until=None,
            details={
                "timestamp": now.isoformat(),
                "old_remaining": current_remaining,
                "new_remaining": new_remaining,
                "change": "decrement",
            },
        )

        # Fire dispatcher signal for immediate sensor update
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")

        _LOGGER.info(
            "Medication %s remaining amount decremented from %s to %s",
            med_data.get(CONF_MEDICATION_NAME),
            current_remaining,
            new_remaining,
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
    if not hass.services.has_service(DOMAIN, SERVICE_INCREMENT_REMAINING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_INCREMENT_REMAINING,
            handle_increment_remaining,
            schema=SERVICE_INCREMENT_REMAINING_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_DECREMENT_REMAINING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DECREMENT_REMAINING,
            handle_decrement_remaining,
            schema=SERVICE_DECREMENT_REMAINING_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
