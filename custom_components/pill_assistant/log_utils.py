"""Utility functions for logging medication events to CSV files."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
import json
import os
import re
from typing import Any

from homeassistant.core import HomeAssistant


LOGS_PARENT_DIR_NAME = "Pill Assistant"
LOGS_DIR_NAME = "Logs"

GLOBAL_LOG_FILENAME = "pill_assistant_all_medications_log.csv"
PER_MED_LOG_SUFFIX = "_log.csv"

GLOBAL_LOG_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "action",
    "medication_id",
    "medication_name",
    "dosage",
    "dosage_unit",
    "remaining_amount",
    "refill_amount",
    "snooze_until",
    "details_json",
)


def _sanitize_filename(value: str) -> str:
    """Return a filesystem-safe filename component."""
    value = value.strip()
    if not value:
        return "unknown"

    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^A-Za-z0-9._-]+", "", value)
    return value or "unknown"


def get_logs_dir(hass: HomeAssistant) -> str:
    """Return the absolute logs folder path."""
    return hass.config.path(LOGS_PARENT_DIR_NAME, LOGS_DIR_NAME)


def get_global_log_path(hass: HomeAssistant) -> str:
    """Return the absolute global CSV log path."""
    return os.path.join(get_logs_dir(hass), GLOBAL_LOG_FILENAME)


def get_medication_log_path(hass: HomeAssistant, medication_name: str) -> str:
    """Return the absolute per-med CSV log path."""
    safe_name = _sanitize_filename(medication_name)
    filename = f"{safe_name}{PER_MED_LOG_SUFFIX}"
    return os.path.join(get_logs_dir(hass), filename)


def _append_csv_row(path: str, columns: tuple[str, ...], row: dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)

        file_exists = os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(columns))
            if not file_exists:
                writer.writeheader()
            writer.writerow({k: row.get(k, "") for k in columns})
    except (
        OSError,
        PermissionError,
    ):  # pragma: no cover - file IO or permission errors
        # Silently ignore errors in test environment or if directory is not writable
        pass


async def async_log_event(
    hass: HomeAssistant,
    *,
    action: str,
    medication_id: str,
    medication_name: str,
    dosage: float | str | None,
    dosage_unit: str | None,
    remaining_amount: float | int | None,
    refill_amount: float | int | None,
    snooze_until: str | None,
    details: dict[str, Any] | None = None,
) -> None:
    """Append an event to both the global CSV and the per-medication CSV."""
    details = details or {}
    timestamp = str(details.get("timestamp", ""))

    row = {
        "timestamp": timestamp,
        "action": action,
        "medication_id": medication_id,
        "medication_name": medication_name,
        "dosage": dosage if dosage is not None else "",
        "dosage_unit": dosage_unit if dosage_unit is not None else "",
        "remaining_amount": remaining_amount if remaining_amount is not None else "",
        "refill_amount": refill_amount if refill_amount is not None else "",
        "snooze_until": snooze_until if snooze_until is not None else "",
        "details_json": json.dumps(details, ensure_ascii=False, sort_keys=True),
    }

    global_path = get_global_log_path(hass)
    med_path = get_medication_log_path(hass, medication_name)

    await hass.async_add_executor_job(
        _append_csv_row, global_path, GLOBAL_LOG_COLUMNS, row
    )
    await hass.async_add_executor_job(
        _append_csv_row, med_path, GLOBAL_LOG_COLUMNS, row
    )


def _read_csv_statistics(
    path: str, start_date: str | None = None, end_date: str | None = None
) -> list[dict[str, Any]]:
    """Read and parse CSV log file, optionally filtering by date range."""
    try:
        if not os.path.exists(path):
            return []

        # Parse date filters
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except (ValueError, TypeError):
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except (ValueError, TypeError):
                pass

        # If no dates provided, default to last 30 days
        if not start_dt and not end_dt:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=30)

        rows = []
        with open(path, "r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                timestamp_str = row.get("timestamp", "")
                if not timestamp_str:
                    continue

                # Filter by date range
                try:
                    row_dt = datetime.fromisoformat(timestamp_str)
                    if start_dt and row_dt < start_dt:
                        continue
                    if end_dt and row_dt > end_dt:
                        continue
                except (ValueError, TypeError):
                    continue

                rows.append(row)

        return rows
    except (OSError, PermissionError):
        return []


async def async_get_statistics(
    hass: HomeAssistant,
    start_date: str | None = None,
    end_date: str | None = None,
    medication_id: str | None = None,
) -> dict[str, Any]:
    """Get medication statistics from CSV logs with on-time tracking."""
    global_path = get_global_log_path(hass)

    # Read CSV data
    rows = await hass.async_add_executor_job(
        _read_csv_statistics, global_path, start_date, end_date
    )

    # Filter by medication_id if provided
    if medication_id:
        rows = [r for r in rows if r.get("medication_id") == medication_id]

    # Get medication configurations for on-time window calculations
    from .const import (
        DOMAIN,
        CONF_SCHEDULE_TIMES,
        CONF_SCHEDULE_DAYS,
        CONF_ON_TIME_WINDOW_MINUTES,
        DEFAULT_ON_TIME_WINDOW_MINUTES,
    )
    
    med_configs = {}
    if hasattr(hass, "data") and DOMAIN in hass.data:
        for med_id, entry_data in hass.data[DOMAIN].items():
            if isinstance(entry_data, dict) and "entry" in entry_data:
                entry = entry_data["entry"]
                med_configs[med_id] = {
                    "schedule_times": entry.data.get(CONF_SCHEDULE_TIMES, []),
                    "schedule_days": entry.data.get(CONF_SCHEDULE_DAYS, []),
                    "on_time_window": entry.data.get(
                        CONF_ON_TIME_WINDOW_MINUTES, DEFAULT_ON_TIME_WINDOW_MINUTES
                    ),
                }

    # Aggregate statistics
    stats = {
        "total_entries": len(rows),
        "medications": {},
        "daily_counts": {},
        "action_counts": {},
    }

    for row in rows:
        med_id = row.get("medication_id", "unknown")
        med_name = row.get("medication_name", "Unknown")
        action = row.get("action", "unknown")
        timestamp_str = row.get("timestamp", "")

        # Aggregate by medication
        if med_id not in stats["medications"]:
            stats["medications"][med_id] = {
                "name": med_name,
                "taken_count": 0,
                "taken_on_time_count": 0,
                "taken_late_count": 0,
                "skipped_count": 0,
                "refilled_count": 0,
                "total_count": 0,
                "on_time_percentage": 0.0,
            }

        stats["medications"][med_id]["total_count"] += 1
        
        if action == "taken":
            stats["medications"][med_id]["taken_count"] += 1
            
            # Calculate if taken on time
            if med_id in med_configs and timestamp_str:
                try:
                    taken_time = datetime.fromisoformat(timestamp_str)
                    config = med_configs[med_id]
                    schedule_times = config["schedule_times"]
                    schedule_days = config["schedule_days"]
                    on_time_window = config["on_time_window"]
                    
                    # Check if taken on a scheduled day
                    day_abbr = taken_time.strftime("%a").lower()[:3]
                    if day_abbr in schedule_days:
                        # Find closest scheduled time
                        taken_minutes = taken_time.hour * 60 + taken_time.minute
                        closest_diff = float('inf')
                        
                        for time_str in schedule_times:
                            try:
                                if isinstance(time_str, list):
                                    time_str = time_str[0] if time_str else "00:00"
                                hour, minute = map(int, time_str.split(":"))
                                scheduled_minutes = hour * 60 + minute
                                diff = abs(taken_minutes - scheduled_minutes)
                                closest_diff = min(closest_diff, diff)
                            except (ValueError, AttributeError):
                                continue
                        
                        # Check if within on-time window
                        if closest_diff <= on_time_window:
                            stats["medications"][med_id]["taken_on_time_count"] += 1
                        else:
                            stats["medications"][med_id]["taken_late_count"] += 1
                    else:
                        # Taken on non-scheduled day counts as late
                        stats["medications"][med_id]["taken_late_count"] += 1
                except (ValueError, TypeError):
                    # If we can't parse, don't count as on-time or late
                    pass
                    
        elif action == "skipped":
            stats["medications"][med_id]["skipped_count"] += 1
        elif action == "refilled":
            stats["medications"][med_id]["refilled_count"] += 1

        # Calculate on-time percentage
        taken_total = stats["medications"][med_id]["taken_count"]
        if taken_total > 0:
            on_time_count = stats["medications"][med_id]["taken_on_time_count"]
            stats["medications"][med_id]["on_time_percentage"] = round(
                (on_time_count / taken_total) * 100, 1
            )

        # Aggregate by day
        try:
            row_dt = datetime.fromisoformat(timestamp_str)
            day_key = row_dt.strftime("%Y-%m-%d")

            if day_key not in stats["daily_counts"]:
                stats["daily_counts"][day_key] = {}

            if med_id not in stats["daily_counts"][day_key]:
                stats["daily_counts"][day_key][med_id] = {
                    "name": med_name,
                    "taken": 0,
                    "skipped": 0,
                }

            if action == "taken":
                stats["daily_counts"][day_key][med_id]["taken"] += 1
            elif action == "skipped":
                stats["daily_counts"][day_key][med_id]["skipped"] += 1
        except (ValueError, TypeError):
            pass

        # Aggregate by action type
        stats["action_counts"][action] = stats["action_counts"].get(action, 0) + 1

    return stats
