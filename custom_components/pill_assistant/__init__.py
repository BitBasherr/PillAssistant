"""Pill Assistant integration for Home Assistant."""

from __future__ import annotations

import csv
from datetime import timedelta
import logging
from pathlib import Path
from typing import Any

try:
    from homeassistant.components.panel_custom import async_register_panel
except ImportError:  # pragma: no cover - fallback for older HA versions
    async_register_panel = None

try:
    from homeassistant.components.frontend import async_remove_panel
except ImportError:  # pragma: no cover - frontend API can vary across HA versions
    async_remove_panel = None
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
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
    ATTR_MEDICATION_ID,
    ATTR_SNOOZE_DURATION,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_REFILL_AMOUNT,
    CONF_NOTIFY_SERVICES,
    DEFAULT_SNOOZE_DURATION_MINUTES,
    ATTR_DOSES_TODAY,
    ATTR_TAKEN_SCHEDULED_RATIO,
    ATTR_LOG_FILE,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Pill Assistant component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pill Assistant from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("panel_registered", False)

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
            ATTR_DOSES_TODAY: [],
        }
        await store.async_save(storage_data)

    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "store": store,
        "storage_data": storage_data,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register admin-only sidebar panel once
    if not hass.data[DOMAIN]["panel_registered"]:
        panel_path = Path(__file__).parent / "panel.js"
        if hasattr(hass, "http"):
            hass.http.register_static_path(
                "/pill_assistant/panel.js",
                str(panel_path),
                cache_headers=False,
            )
        if async_register_panel:
            await async_register_panel(
                hass,
                webcomponent_name="ha-panel-pill-assistant",
                frontend_url_path="pill-assistant",
                module_url="/pill_assistant/panel.js",
                sidebar_title="Pill Assistant",
                sidebar_icon="mdi:pill",
                require_admin=True,
                config={"log_path": hass.config.path(LOG_FILE_NAME)},
            )
            hass.data[DOMAIN]["panel_registered"] = True
        else:  # pragma: no cover - defensive for older HA builds
            _LOGGER.warning("Custom panel registration unavailable on this HA build")

    # Create helper button for testing notification pipeline
    try:
        med_name = entry.data.get(CONF_MEDICATION_NAME, "Medication")
        button_object_id = f"pa_{med_name.lower().replace(' ', '_')}_test"
        await hass.services.async_call(
            "input_button",
            "create",
            {
                "name": f"PA_{med_name} Test Notification",
                "icon": "mdi:bell-alert",
                "entity_id": f"input_button.{button_object_id}",
            },
            blocking=False,
        )
    except Exception:  # pragma: no cover - helper may not be available in tests
        _LOGGER.debug("input_button helper unavailable; skipping helper creation")

    # Register services
    async def _send_notification(
        med_id: str, med_data: dict[str, Any], *, is_test: bool = False
    ) -> None:
        """Send a structured notification for a medication."""
        med_name = med_data.get(CONF_MEDICATION_NAME, "Unknown")
        dosage = med_data.get(CONF_DOSAGE, "")
        dosage_unit = med_data.get(CONF_DOSAGE_UNIT, "")
        notify_services = med_data.get(CONF_NOTIFY_SERVICES, [])

        message = f"Time to take {dosage} {dosage_unit} of {med_name}".strip()
        title = "Medication Reminder"
        if is_test:
            title += " (Test)"

        payload: dict[str, Any] = {
            "title": title,
            "message": message,
            "data": {
                "tag": f"pill_assistant_{med_id}",
                "actions": [
                    {
                        "action": f"take_medication_{med_id}",
                        "title": "Mark as Taken",
                        "service": f"{DOMAIN}.{SERVICE_TAKE_MEDICATION}",
                        "service_data": {ATTR_MEDICATION_ID: med_id},
                    },
                    {
                        "action": f"snooze_medication_{med_id}",
                        "title": "Snooze",
                        "service": f"{DOMAIN}.{SERVICE_SNOOZE_MEDICATION}",
                        "service_data": {ATTR_MEDICATION_ID: med_id},
                    },
                ],
            },
        }

        if notify_services:
            for service_name in notify_services:
                try:
                    service_parts = service_name.split(".")
                    if len(service_parts) == 2:
                        domain, service = service_parts
                        await hass.services.async_call(
                            domain,
                            service,
                            payload,
                            blocking=False,
                        )
                except Exception as exc:  # pragma: no cover - runtime safety
                    _LOGGER.error(
                        "Failed to send notification via %s: %s", service_name, exc
                    )
        else:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"pill_assistant_{med_id}",
                },
                blocking=False,
            )

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

        # Track doses taken today
        today_prefix = now.date().isoformat()
        doses_today = [
            ts
            for ts in med_data.get(ATTR_DOSES_TODAY, [])
            if ts.startswith(today_prefix)
        ]
        doses_today.append(now.isoformat())
        med_data[ATTR_DOSES_TODAY] = doses_today

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
        log_path = Path(hass.config.path(LOG_FILE_NAME))
        log_line = [
            now.strftime("%Y-%m-%d %H:%M:%S"),
            "TAKEN",
            med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            med_data.get(CONF_DOSAGE, ""),
            med_data.get(CONF_DOSAGE_UNIT, ""),
        ]
        try:
            new_file = not log_path.exists()
            with log_path.open("a", encoding="utf-8", newline="") as log_file:
                writer = csv.writer(log_file)
                if new_file:
                    writer.writerow(
                        [
                            "timestamp",
                            "event",
                            "medication_name",
                            "dosage",
                            "dosage_unit",
                        ]
                    )
                writer.writerow(log_line)
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
        log_path = Path(hass.config.path(LOG_FILE_NAME))
        log_line = [
            now.strftime("%Y-%m-%d %H:%M:%S"),
            "SKIPPED",
            med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            "",
            "",
        ]
        try:
            new_file = not log_path.exists()
            with log_path.open("a", encoding="utf-8", newline="") as log_file:
                writer = csv.writer(log_file)
                if new_file:
                    writer.writerow(
                        [
                            "timestamp",
                            "event",
                            "medication_name",
                            "dosage",
                            "dosage_unit",
                        ]
                    )
                writer.writerow(log_line)
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
        log_path = Path(hass.config.path(LOG_FILE_NAME))
        log_line = [
            now.strftime("%Y-%m-%d %H:%M:%S"),
            "REFILLED",
            med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            refill_amount,
            "units",
        ]
        try:
            new_file = not log_path.exists()
            with log_path.open("a", encoding="utf-8", newline="") as log_file:
                writer = csv.writer(log_file)
                if new_file:
                    writer.writerow(
                        [
                            "timestamp",
                            "event",
                            "medication_name",
                            "dosage",
                            "dosage_unit",
                        ]
                    )
                writer.writerow(log_line)
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

        await _send_notification(med_id, med_data, is_test=True)

        _LOGGER.info(
            "Test notification sent for %s", med_data.get(CONF_MEDICATION_NAME)
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

    # Register services only once
    if not hass.services.has_service(DOMAIN, SERVICE_TAKE_MEDICATION):
        hass.services.async_register(
            DOMAIN, SERVICE_TAKE_MEDICATION, handle_take_medication
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SKIP_MEDICATION):
        hass.services.async_register(
            DOMAIN, SERVICE_SKIP_MEDICATION, handle_skip_medication
        )
    if not hass.services.has_service(DOMAIN, SERVICE_REFILL_MEDICATION):
        hass.services.async_register(
            DOMAIN, SERVICE_REFILL_MEDICATION, handle_refill_medication
        )
    if not hass.services.has_service(DOMAIN, SERVICE_TEST_NOTIFICATION):
        hass.services.async_register(
            DOMAIN, SERVICE_TEST_NOTIFICATION, handle_test_notification
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SNOOZE_MEDICATION):
        hass.services.async_register(
            DOMAIN, SERVICE_SNOOZE_MEDICATION, handle_snooze_medication
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and tear down the panel when no entries remain."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id, None)

    if (
        unload_ok
        and len(hass.data.get(DOMAIN, {})) <= 1
        and hass.data[DOMAIN].get("panel_registered")
    ):
        if async_remove_panel:
            await async_remove_panel(hass, "pill-assistant")
        hass.data[DOMAIN]["panel_registered"] = False

    return unload_ok
