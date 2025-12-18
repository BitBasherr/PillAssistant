from __future__ import annotations

import csv
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
    os.makedirs(os.path.dirname(path), exist_ok=True)

    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in columns})


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

    await hass.async_add_executor_job(_append_csv_row, global_path, GLOBAL_LOG_COLUMNS, row)
    await hass.async_add_executor_job(_append_csv_row, med_path, GLOBAL_LOG_COLUMNS, row)
