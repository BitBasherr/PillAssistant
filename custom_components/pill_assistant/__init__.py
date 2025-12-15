"""Pill Assistant integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

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
    ATTR_MEDICATION_ID,
    CONF_MEDICATION_NAME,
    CONF_REFILL_AMOUNT,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Pill Assistant component."""
    hass.data.setdefault(DOMAIN, {})
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
        
        # Decrease remaining amount
        dosage = float(med_data.get(CONF_REFILL_AMOUNT, 1))
        remaining = float(med_data.get("remaining_amount", 0))
        med_data["remaining_amount"] = max(0, remaining - dosage)
        
        # Add to history
        history_entry = {
            "medication_id": med_id,
            "medication_name": med_data.get(CONF_MEDICATION_NAME, "Unknown"),
            "timestamp": now.isoformat(),
            "action": "taken",
            "dosage": med_data.get("dosage", ""),
            "dosage_unit": med_data.get("dosage_unit", ""),
        }
        storage_data["history"].append(history_entry)
        
        # Save to storage
        await store.async_save(storage_data)
        
        # Append to persistent log file
        log_path = hass.config.path(LOG_FILE_NAME)
        log_line = f"{now.strftime('%Y-%m-%d %H:%M:%S')} - TAKEN - {med_data.get(CONF_MEDICATION_NAME, 'Unknown')} - {med_data.get('dosage', '')} {med_data.get('dosage_unit', '')}\n"
        try:
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(log_line)
        except Exception as e:
            _LOGGER.error("Failed to write to log file: %s", e)
        
        _LOGGER.info("Medication %s taken at %s", med_data.get(CONF_MEDICATION_NAME), now)
    
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
        
        _LOGGER.info("Medication %s skipped at %s", med_data.get(CONF_MEDICATION_NAME), now)
    
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
        
        _LOGGER.info("Medication %s refilled to %s at %s", med_data.get(CONF_MEDICATION_NAME), refill_amount, now)
    
    # Register services only once
    if not hass.services.has_service(DOMAIN, SERVICE_TAKE_MEDICATION):
        hass.services.async_register(DOMAIN, SERVICE_TAKE_MEDICATION, handle_take_medication)
    if not hass.services.has_service(DOMAIN, SERVICE_SKIP_MEDICATION):
        hass.services.async_register(DOMAIN, SERVICE_SKIP_MEDICATION, handle_skip_medication)
    if not hass.services.has_service(DOMAIN, SERVICE_REFILL_MEDICATION):
        hass.services.async_register(DOMAIN, SERVICE_REFILL_MEDICATION, handle_refill_medication)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    
    return unload_ok
