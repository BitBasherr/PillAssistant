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
from homeassistant.helpers.typing import ConfigType
import homeassistant.util.dt as dt_util

from .store import PillAssistantStore

try:  # HA version compatibility: StaticPathConfig may not exist in tests
    from homeassistant.components.http import StaticPathConfig
except ImportError:  # pragma: no cover - older HA / test env without StaticPathConfig
    StaticPathConfig = None  # type: ignore[assignment]

from .const import (
    ATTR_ACTION,
    ATTR_AMOUNT,
    ATTR_DOSAGE,
    ATTR_DOSAGE_UNIT,
    ATTR_END_DATE,
    ATTR_HISTORY_INDEX,
    ATTR_MEDICATION_ID,
    ATTR_SNOOZE_DURATION,
    ATTR_START_DATE,
    ATTR_TIMESTAMP,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_MEDICATION_NAME,
    CONF_MEDICATION_TYPE,
    CONF_NOTIFY_SERVICES,
    CONF_REFILL_AMOUNT,
    CONF_CURRENT_QUANTITY,
    CONF_SCHEDULE_TYPE,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_RELATIVE_TO_SENSOR,
    CONF_AVOID_DUPLICATE_TRIGGERS,
    DEFAULT_SNOOZE_DURATION_MINUTES,
    DEFAULT_MEDICATION_TYPE,
    DEFAULT_DOSAGE_UNIT,
    DEFAULT_AVOID_DUPLICATE_TRIGGERS,
    DOMAIN,
    LEGACY_DOSAGE_UNITS,
    DOSAGE_UNIT_OPTIONS,
    SERVICE_DECREMENT_DOSAGE,
    SERVICE_DECREMENT_REMAINING,
    SERVICE_DELETE_MEDICATION_HISTORY,
    SERVICE_EDIT_MEDICATION_HISTORY,
    SERVICE_GET_MEDICATION_HISTORY,
    SERVICE_GET_STATISTICS,
    SERVICE_INCREMENT_DOSAGE,
    SERVICE_INCREMENT_REMAINING,
    SERVICE_REFILL_MEDICATION,
    SERVICE_SKIP_MEDICATION,
    SERVICE_SNOOZE_MEDICATION,
    SERVICE_TAKE_MEDICATION,
    SERVICE_TEST_NOTIFICATION,
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

SERVICE_GET_STATISTICS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_MEDICATION_ID): cv.string,
        vol.Optional(ATTR_START_DATE): cv.string,
        vol.Optional(ATTR_END_DATE): cv.string,
    },
)

SERVICE_GET_MEDICATION_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_MEDICATION_ID): cv.string,
        vol.Optional(ATTR_START_DATE): cv.string,
        vol.Optional(ATTR_END_DATE): cv.string,
    },
)

SERVICE_EDIT_MEDICATION_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_HISTORY_INDEX): vol.Coerce(int),
        vol.Optional(ATTR_TIMESTAMP): cv.string,
        vol.Optional(ATTR_ACTION): cv.string,
        vol.Optional(ATTR_DOSAGE): vol.Coerce(float),
        vol.Optional(ATTR_DOSAGE_UNIT): cv.string,
        vol.Optional(ATTR_AMOUNT): vol.Coerce(float),
    },
)

SERVICE_DELETE_MEDICATION_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_HISTORY_INDEX): vol.Coerce(int),
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

    # Migrate legacy dosage_unit format to separate medication_type and dosage_unit
    needs_migration = CONF_MEDICATION_TYPE not in entry.data
    if needs_migration:
        _LOGGER.info(
            "Upgrading medication configuration for '%s' to separate dosage and medication type",
            entry.data.get(CONF_MEDICATION_NAME, "Unknown"),
        )
        migrated_data = entry.data.copy()
        dosage_unit = entry.data.get(CONF_DOSAGE_UNIT, DEFAULT_DOSAGE_UNIT)

        # Check if this is a legacy dosage unit
        if dosage_unit in LEGACY_DOSAGE_UNITS:
            med_type, unit = LEGACY_DOSAGE_UNITS[dosage_unit]
            migrated_data[CONF_MEDICATION_TYPE] = med_type
            migrated_data[CONF_DOSAGE_UNIT] = unit
            _LOGGER.info(
                "Migrated '%s' from '%s' to type='%s', unit='%s'",
                entry.data.get(CONF_MEDICATION_NAME),
                dosage_unit,
                med_type,
                unit,
            )
        else:
            # Unknown format - assign default medication type
            migrated_data[CONF_MEDICATION_TYPE] = DEFAULT_MEDICATION_TYPE
            # Keep existing dosage_unit if it's valid
            valid_units = [opt["value"] for opt in DOSAGE_UNIT_OPTIONS]
            if dosage_unit not in valid_units:
                migrated_data[CONF_DOSAGE_UNIT] = DEFAULT_DOSAGE_UNIT
            _LOGGER.info(
                "Assigned default medication type '%s' for '%s'",
                DEFAULT_MEDICATION_TYPE,
                entry.data.get(CONF_MEDICATION_NAME),
            )

        # Update the config entry with migrated data
        hass.config_entries.async_update_entry(entry, data=migrated_data)

    # Get or create the singleton storage instance
    if "store" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["store"] = PillAssistantStore(hass)

    store = hass.data[DOMAIN]["store"]

    # Load storage data (this will use the cached data from the singleton)
    storage_data = await store.async_load()

    # Store the entry data in storage if not already there
    med_id = entry.entry_id
    if med_id not in storage_data["medications"]:
        # Use current_quantity if provided (from custom starting amount), otherwise use refill_amount
        starting_amount = entry.data.get(
            CONF_CURRENT_QUANTITY, entry.data.get(CONF_REFILL_AMOUNT, 0)
        )

        # Use the async_update method for atomic updates
        def add_medication(data: dict) -> None:
            data["medications"][med_id] = {
                **entry.data,
                "remaining_amount": starting_amount,
                "last_taken": None,
                "missed_doses": [],
            }

        await store.async_update(add_medication)

    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "store": store,
        "storage_data": storage_data,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register notification action listener ONCE globally (not per entry)
    if not hass.data[DOMAIN].get("notification_listeners_registered"):

        async def handle_notification_action(event) -> None:
            """Handle notification action events from mobile_app."""
            action = event.data.get("action")
            if not action:
                return

            # Parse the action to extract medication ID
            if action.startswith("take_medication_"):
                _med_id = action.replace("take_medication_", "")
                if _med_id in hass.data[DOMAIN]:
                    # Directly mark as taken to ensure the action works even when
                    # ServiceRegistry.async_call is patched in tests.
                    await _mark_med_taken(_med_id)
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

        hass.data[DOMAIN]["notification_listeners_registered"] = True
        _LOGGER.debug("Notification action listeners registered globally")

    # Register services
    async def _mark_med_taken(_med_id: str, _now: datetime | None = None) -> None:
        """Mark medication as taken (shared helper)."""
        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data_local = hass.data[DOMAIN][_med_id]
        _store_local = entry_data_local["store"]
        _entry_local = entry_data_local["entry"]

        now_local = _now or dt_util.now()

        # Helper to compute next fixed-time scheduled occurrence after a reference time
        def _next_fixed_time_after(schedule_times: list, schedule_days: list, reference: datetime) -> datetime | None:
            if not schedule_times or not schedule_days:
                return None
            # Normalize days to 3-letter lower-case
            days = [d.lower() for d in schedule_days]
            for day_offset in range(8):
                check_date = reference + timedelta(days=day_offset)
                check_day = check_date.strftime("%a").lower()[:3]
                if check_day not in days:
                    continue
                for time_str in schedule_times:
                    try:
                        if isinstance(time_str, list):
                            time_str = time_str[0] if time_str else "00:00"
                        hour, minute = map(int, time_str.split(":"))
                        dose_time = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if dose_time > reference:
                            return dose_time
                    except (ValueError, AttributeError):
                        continue
            return None

        def update_medication(data: dict) -> None:
            """Update medication data atomically."""
            med_data = data["medications"].get(_med_id)
            if not med_data:
                _LOGGER.error("Medication data for %s not found", _med_id)
                return

            # If this is a fixed-time schedule and there's a next scheduled occurrence,
            # assume the manual take consumes the upcoming scheduled dose and set the
            # recorded last_taken to that scheduled time (so the next dose will be the
            # following scheduled occurrence). This matches expected reshuffle behavior.
            schedule_type_local = _entry_local.data.get(CONF_SCHEDULE_TYPE)
            if schedule_type_local == "fixed_time":
                schedule_times = _entry_local.data.get(CONF_SCHEDULE_TIMES, [])
                schedule_days = _entry_local.data.get(CONF_SCHEDULE_DAYS, [])
                next_sched = _next_fixed_time_after(schedule_times, schedule_days, now_local)
                if next_sched:
                    med_data["last_taken"] = next_sched.isoformat()
                else:
                    med_data["last_taken"] = now_local.isoformat()
            else:
                # Update last taken time
                med_data["last_taken"] = now_local.isoformat()

            # Decrease remaining amount by 1 dose (not by dosage amount)
            remaining = float(med_data.get("remaining_amount", 0))
            med_data["remaining_amount"] = max(0, remaining - 1)

            # If this is a sensor-based schedule with duplicate avoidance, track the trigger
            schedule_type = _entry_local.data.get(CONF_SCHEDULE_TYPE)
            if schedule_type == "relative_sensor":
                avoid_duplicates = _entry_local.data.get(
                    CONF_AVOID_DUPLICATE_TRIGGERS, DEFAULT_AVOID_DUPLICATE_TRIGGERS
                )
                if avoid_duplicates:
                    sensor_entity_id = _entry_local.data.get(CONF_RELATIVE_TO_SENSOR)
                    if sensor_entity_id:
                        sensor_state = hass.states.get(sensor_entity_id)
                        if sensor_state and sensor_state.last_changed:
                            # Track this sensor event as triggered
                            if "last_sensor_trigger" not in data:
                                data["last_sensor_trigger"] = {}
                            data["last_sensor_trigger"][
                                _med_id
                            ] = sensor_state.last_changed.isoformat()

            # Add to history
            history_entry = {
                "medication_id": _med_id,
                "medication_name": med_data.get(CONF_MEDICATION_NAME, "Unknown"),
                "timestamp": now_local.isoformat(),
                "action": "taken",
                "dosage": med_data.get(CONF_DOSAGE, ""),
                "dosage_unit": med_data.get(CONF_DOSAGE_UNIT, ""),
            }
            data["history"].append(history_entry)

        await _store_local.async_update(update_medication)

        # Reload storage data to get updated values for logging
        storage_data = await _store_local.async_load()
        med_data = storage_data["medications"].get(_med_id, {})

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
            details={"timestamp": now_local.isoformat()},
        )

        # Fire dispatcher signal for immediate sensor update (per-med and global)
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")
        async_dispatcher_send(hass, SIGNAL_MEDICATION_UPDATED)

        _LOGGER.info(
            "Medication %s taken at %s",
            med_data.get(CONF_MEDICATION_NAME),
            now_local,
        )

    async def handle_take_medication(call: ServiceCall) -> None:
        """Handle take medication service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        await _mark_med_taken(_med_id)

    async def handle_skip_medication(call: ServiceCall) -> None:
        """Handle skip medication service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        if _med_id not in hass.data[DOMAIN]:
            _LOGGER.error("Medication ID %s not found", _med_id)
            return

        entry_data = hass.data[DOMAIN][_med_id]
        _store = entry_data["store"]

        now = dt_util.now()

        def update_skip(data: dict) -> None:
            """Update medication data atomically."""
            med_data = data["medications"].get(_med_id)
            if not med_data:
                return

            # Add to history
            history_entry = {
                "medication_id": _med_id,
                "medication_name": med_data.get(CONF_MEDICATION_NAME, "Unknown"),
                "timestamp": now.isoformat(),
                "action": "skipped",
            }
            data["history"].append(history_entry)

        await _store.async_update(update_skip)

        # Reload for logging
        storage_data = await _store.async_load()
        med_data = storage_data["medications"].get(_med_id, {})

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

        # Fire dispatcher signal for immediate sensor update (per-med and global)
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")
        async_dispatcher_send(hass, SIGNAL_MEDICATION_UPDATED)

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

        now = dt_util.now()

        def update_refill(data: dict) -> None:
            """Update medication data atomically."""
            med_data = data["medications"].get(_med_id)
            if not med_data:
                return

            # Reset to full refill amount
            refill_amount = med_data.get(CONF_REFILL_AMOUNT, 0)
            med_data["remaining_amount"] = refill_amount

            # Add to history
            history_entry = {
                "medication_id": _med_id,
                "medication_name": med_data.get(CONF_MEDICATION_NAME, "Unknown"),
                "timestamp": now.isoformat(),
                "action": "refilled",
                "amount": refill_amount,
            }
            data["history"].append(history_entry)

        await _store.async_update(update_refill)

        # Reload for logging
        storage_data = await _store.async_load()
        med_data = storage_data["medications"].get(_med_id, {})
        refill_amount = med_data.get(CONF_REFILL_AMOUNT, 0)

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

        # Fire dispatcher signal for immediate sensor update (per-med and global)
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")
        async_dispatcher_send(hass, SIGNAL_MEDICATION_UPDATED)

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
        _store = entry_data["store"]

        # Load current storage data
        storage_data = await _store.async_load()
        med_data = storage_data["medications"].get(_med_id)
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

        # Calculate snooze until time
        now = dt_util.now()
        snooze_until = now + timedelta(minutes=int(snooze_duration))

        def update_snooze(data: dict) -> None:
            """Update medication data atomically."""
            med_data = data["medications"].get(_med_id)
            if not med_data:
                return

            # Store snooze information
            med_data["snooze_until"] = snooze_until.isoformat()

        await _store.async_update(update_snooze)

        # Reload for logging
        storage_data = await _store.async_load()
        med_data = storage_data["medications"].get(_med_id, {})

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

        # Fire dispatcher signal for immediate sensor update (per-med and global)
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")
        async_dispatcher_send(hass, SIGNAL_MEDICATION_UPDATED)

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

        # Get timestamp
        now = dt_util.now()

        current_dosage = None
        new_dosage = None

        def update_dosage(data: dict) -> None:
            """Update medication data atomically."""
            nonlocal current_dosage, new_dosage
            med_data = data["medications"].get(_med_id)
            if not med_data:
                return

            # Increment dosage by 0.5 (works for pills, tablets, etc.)
            current_dosage = float(med_data.get(CONF_DOSAGE, 1))
            new_dosage = current_dosage + 0.5
            med_data[CONF_DOSAGE] = str(new_dosage)

        await _store.async_update(update_dosage)

        # Reload for logging
        storage_data = await _store.async_load()
        med_data = storage_data["medications"].get(_med_id, {})

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

        # Fire dispatcher signal for immediate sensor update (per-med and global)
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")
        async_dispatcher_send(hass, SIGNAL_MEDICATION_UPDATED)

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

        # Get timestamp
        now = dt_util.now()

        current_dosage = None
        new_dosage = None

        def update_dosage(data: dict) -> None:
            """Update medication data atomically."""
            nonlocal current_dosage, new_dosage
            med_data = data["medications"].get(_med_id)
            if not med_data:
                return

            # Decrement dosage by 0.5 (works for pills, tablets, etc.), minimum 0.5
            current_dosage = float(med_data.get(CONF_DOSAGE, 1))
            new_dosage = max(0.5, current_dosage - 0.5)
            med_data[CONF_DOSAGE] = str(new_dosage)

        await _store.async_update(update_dosage)

        # Reload for logging
        storage_data = await _store.async_load()
        med_data = storage_data["medications"].get(_med_id, {})

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

        # Fire dispatcher signal for immediate sensor update (per-med and global)
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")
        async_dispatcher_send(hass, SIGNAL_MEDICATION_UPDATED)

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

        # Get timestamp
        now = dt_util.now()

        current_remaining = None
        new_remaining = None

        def update_remaining(data: dict) -> None:
            """Update medication data atomically."""
            nonlocal current_remaining, new_remaining
            med_data = data["medications"].get(_med_id)
            if not med_data:
                return

            # Increment remaining amount by dosage amount
            current_dosage = float(med_data.get(CONF_DOSAGE, 1))
            current_remaining = float(med_data.get("remaining_amount", 0))
            new_remaining = current_remaining + current_dosage
            med_data["remaining_amount"] = new_remaining

        await _store.async_update(update_remaining)

        # Reload for logging
        storage_data = await _store.async_load()
        med_data = storage_data["medications"].get(_med_id, {})

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

        # Fire dispatcher signal for immediate sensor update (per-med and global)
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")
        async_dispatcher_send(hass, SIGNAL_MEDICATION_UPDATED)

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

        # Get timestamp
        now = dt_util.now()

        current_remaining = None
        new_remaining = None

        def update_remaining(data: dict) -> None:
            """Update medication data atomically."""
            nonlocal current_remaining, new_remaining
            med_data = data["medications"].get(_med_id)
            if not med_data:
                return

            # Decrement remaining amount by dosage amount, minimum 0
            current_dosage = float(med_data.get(CONF_DOSAGE, 1))
            current_remaining = float(med_data.get("remaining_amount", 0))
            new_remaining = max(0, current_remaining - current_dosage)
            med_data["remaining_amount"] = new_remaining

        await _store.async_update(update_remaining)

        # Reload for logging
        storage_data = await _store.async_load()
        med_data = storage_data["medications"].get(_med_id, {})

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

        # Fire dispatcher signal for immediate sensor update (per-med and global)
        async_dispatcher_send(hass, f"{SIGNAL_MEDICATION_UPDATED}_{_med_id}")
        async_dispatcher_send(hass, SIGNAL_MEDICATION_UPDATED)

        _LOGGER.info(
            "Medication %s remaining amount decremented from %s to %s",
            med_data.get(CONF_MEDICATION_NAME),
            current_remaining,
            new_remaining,
        )

    async def handle_get_statistics(call: ServiceCall) -> dict:
        """Handle get statistics service."""
        _med_id = call.data.get(ATTR_MEDICATION_ID)
        start_date = call.data.get(ATTR_START_DATE)
        end_date = call.data.get(ATTR_END_DATE)

        stats = await log_utils.async_get_statistics(
            hass,
            start_date=start_date,
            end_date=end_date,
            medication_id=_med_id,
        )

        _LOGGER.info("Statistics retrieved: %s entries", stats["total_entries"])
        return stats

    async def handle_get_medication_history(call: ServiceCall) -> dict:
        """Handle get medication history service."""
        from datetime import datetime

        _med_id = call.data.get(ATTR_MEDICATION_ID)
        start_date_str = call.data.get(ATTR_START_DATE)
        end_date_str = call.data.get(ATTR_END_DATE)

        # Parse date filters if provided (make them timezone-aware)
        start_date = None
        end_date = None
        if start_date_str:
            try:
                parsed = dt_util.parse_datetime(start_date_str)
                if parsed is None:
                    raise ValueError("Invalid datetime")
                # If naive, make it timezone-aware using the system timezone
                if parsed.tzinfo is None:
                    start_date = dt_util.as_local(
                        dt_util.utc_from_timestamp(parsed.timestamp())
                    )
                else:
                    start_date = dt_util.as_local(parsed)
            except (ValueError, OSError, TypeError):
                _LOGGER.warning("Invalid start_date format: %s", start_date_str)
        if end_date_str:
            try:
                parsed = dt_util.parse_datetime(end_date_str)
                if parsed is None:
                    raise ValueError("Invalid datetime")
                # If naive, make it timezone-aware using the system timezone
                if parsed.tzinfo is None:
                    end_date = dt_util.as_local(
                        dt_util.utc_from_timestamp(parsed.timestamp())
                    )
                else:
                    end_date = dt_util.as_local(parsed)
            except (ValueError, OSError, TypeError):
                _LOGGER.warning("Invalid end_date format: %s", end_date_str)

        # Get storage data from any medication entry (they all share the same storage)
        _store = None
        for entry_id in hass.data.get(DOMAIN, {}):
            if entry_id not in [
                "panel_registered",
                "sidebar_registered",
                "store",
                "notification_listeners_registered",
            ]:
                entry_data = hass.data[DOMAIN].get(entry_id)
                if entry_data and isinstance(entry_data, dict):
                    _store = entry_data.get("store")
                    if _store:
                        break

        if not _store:
            _LOGGER.warning("No storage available")
            return {"history": [], "total_entries": 0}

        # Load current storage data
        _storage_data = await _store.async_load()

        # Get all history entries
        all_history = _storage_data.get("history", [])

        # Filter by medication_id if provided
        filtered_history = []
        for idx, entry in enumerate(all_history):
            # Add index to each entry for editing/deletion
            entry_with_index = entry.copy()
            entry_with_index["history_index"] = idx

            # Filter by medication_id
            if _med_id and entry.get("medication_id") != _med_id:
                continue

            # Filter by date range
            if start_date or end_date:
                try:
                    parsed = datetime.fromisoformat(
                        entry.get("timestamp", "").replace("Z", "+00:00")
                    )
                    # Ensure timestamp is timezone-aware
                    if parsed.tzinfo is None:
                        entry_timestamp = dt_util.as_local(
                            dt_util.utc_from_timestamp(parsed.timestamp())
                        )
                    else:
                        entry_timestamp = parsed

                    if start_date and entry_timestamp < start_date:
                        continue
                    if end_date and entry_timestamp > end_date:
                        continue
                except (ValueError, AttributeError, OSError):
                    continue

            filtered_history.append(entry_with_index)

        # Sort by timestamp descending (most recent first)
        filtered_history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        _LOGGER.info("Medication history retrieved: %s entries", len(filtered_history))
        return {"history": filtered_history, "total_entries": len(filtered_history)}

    async def handle_edit_medication_history(call: ServiceCall) -> dict:
        """Handle edit medication history service."""
        history_index = call.data.get(ATTR_HISTORY_INDEX)
        new_timestamp = call.data.get(ATTR_TIMESTAMP)
        new_action = call.data.get(ATTR_ACTION)
        new_dosage = call.data.get(ATTR_DOSAGE)
        new_dosage_unit = call.data.get(ATTR_DOSAGE_UNIT)
        new_amount = call.data.get(ATTR_AMOUNT)

        # Get storage from any medication entry
        _store = None
        for entry_id in hass.data.get(DOMAIN, {}):
            if entry_id not in [
                "panel_registered",
                "sidebar_registered",
                "store",
                "notification_listeners_registered",
            ]:
                entry_data = hass.data[DOMAIN].get(entry_id)
                if entry_data and isinstance(entry_data, dict):
                    _store = entry_data.get("store")
                    if _store:
                        break

        if not _store:
            _LOGGER.error("Storage not available for editing history")
            return {"success": False, "error": "Storage not available"}

        updated_entry = None

        def update_history(data: dict) -> None:
            """Update medication history atomically."""
            nonlocal updated_entry

            # Get all history entries
            all_history = data.get("history", [])

            # Validate index
            if history_index < 0 or history_index >= len(all_history):
                _LOGGER.error("Invalid history index: %s", history_index)
                return

            # Update the entry
            entry = all_history[history_index]
            if new_timestamp:
                entry["timestamp"] = new_timestamp
            if new_action:
                entry["action"] = new_action
            if new_dosage is not None:
                entry["dosage"] = new_dosage
            if new_dosage_unit:
                entry["dosage_unit"] = new_dosage_unit
            if new_amount is not None:
                entry["amount"] = new_amount

            updated_entry = entry.copy()

        await _store.async_update(update_history)

        if updated_entry:
            _LOGGER.info(
                "Medication history entry %s edited successfully", history_index
            )
            return {"success": True, "updated_entry": updated_entry}
        else:
            return {"success": False, "error": "Invalid history index"}

    async def handle_delete_medication_history(call: ServiceCall) -> dict:
        """Handle delete medication history service."""
        history_index = call.data.get(ATTR_HISTORY_INDEX)

        # Get storage from any medication entry
        _store = None
        for entry_id in hass.data.get(DOMAIN, {}):
            if entry_id not in [
                "panel_registered",
                "sidebar_registered",
                "store",
                "notification_listeners_registered",
            ]:
                entry_data = hass.data[DOMAIN].get(entry_id)
                if entry_data and isinstance(entry_data, dict):
                    _store = entry_data.get("store")
                    if _store:
                        break

        if not _store:
            _LOGGER.error("Storage not available for deleting history")
            return {"success": False, "error": "Storage not available"}

        deleted_entry = None

        def delete_history(data: dict) -> None:
            """Delete medication history atomically."""
            nonlocal deleted_entry

            # Get all history entries
            all_history = data.get("history", [])

            # Validate index
            if history_index < 0 or history_index >= len(all_history):
                _LOGGER.error("Invalid history index: %s", history_index)
                return

            # Delete the entry
            deleted_entry = all_history.pop(history_index)

        await _store.async_update(delete_history)

        if deleted_entry:
            _LOGGER.info(
                "Medication history entry %s deleted successfully", history_index
            )
            return {"success": True, "deleted_entry": deleted_entry}
        else:
            return {"success": False, "error": "Invalid history index"}

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
    if not hass.services.has_service(DOMAIN, SERVICE_GET_STATISTICS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_STATISTICS,
            handle_get_statistics,
            schema=SERVICE_GET_STATISTICS_SCHEMA,
            supports_response=True,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_GET_MEDICATION_HISTORY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_MEDICATION_HISTORY,
            handle_get_medication_history,
            schema=SERVICE_GET_MEDICATION_HISTORY_SCHEMA,
            supports_response=True,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_EDIT_MEDICATION_HISTORY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_EDIT_MEDICATION_HISTORY,
            handle_edit_medication_history,
            schema=SERVICE_EDIT_MEDICATION_HISTORY_SCHEMA,
            supports_response=True,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_DELETE_MEDICATION_HISTORY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DELETE_MEDICATION_HISTORY,
            handle_delete_medication_history,
            schema=SERVICE_DELETE_MEDICATION_HISTORY_SCHEMA,
            supports_response=True,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
