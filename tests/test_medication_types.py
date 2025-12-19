"""Test new medication types."""

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.pill_assistant.const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_MEDICATION_TYPE,
    CONF_SCHEDULE_TYPE,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    DOSAGE_UNIT_OPTIONS,
    MEDICATION_TYPE_OPTIONS,
)


@pytest.mark.parametrize(
    "medication_type",
    [
        "gummy",
        "syrup",
        "gelatin_capsule",
    ],
)
async def test_new_medication_types(hass: HomeAssistant, medication_type: str):
    """Test that new medication types are accepted in config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    # Test with new medication type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: f"Test Med {medication_type}",
            CONF_DOSAGE: "1",
            CONF_MEDICATION_TYPE: medication_type,
            CONF_DOSAGE_UNIT: "each",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "schedule"


async def test_all_dosage_unit_options_exist(hass: HomeAssistant):
    """Test that all expected dosage unit options exist."""
    expected_units = [
        "each",
        "mL",
        "mg",
        "g",
        "mcg",
        "tsp",
        "TBSP",
        "units",
        "IU",
    ]

    available_units = [option["value"] for option in DOSAGE_UNIT_OPTIONS]

    for unit in expected_units:
        assert unit in available_units, f"Dosage unit {unit} not found in options"


async def test_all_medication_type_options_exist(hass: HomeAssistant):
    """Test that all expected medication type options exist."""
    expected_types = [
        "pill",
        "tablet",
        "capsule",
        "gelatin_capsule",
        "gummy",
        "liquid",
        "syrup",
        "drop",
        "spray",
        "puff",
    ]

    available_types = [option["value"] for option in MEDICATION_TYPE_OPTIONS]

    for med_type in expected_types:
        assert (
            med_type in available_types
        ), f"Medication type {med_type} not found in options"


async def test_gummy_medication_full_flow(hass: HomeAssistant):
    """Test full config flow with gummy medication type."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Step 1: Medication details with gummy type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Vitamin Gummies",
            CONF_DOSAGE: "2",
            CONF_MEDICATION_TYPE: "gummy",
            CONF_DOSAGE_UNIT: "each",
        },
    )

    # Step 2: Schedule type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TYPE: "fixed_time",
        },
    )

    # Step 3: Fixed time schedule
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["08:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    # Step 4: Refill settings - this should create the entry
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 60,
            CONF_REFILL_REMINDER_DAYS: 7,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vitamin Gummies"
    assert result["data"][CONF_MEDICATION_TYPE] == "gummy"
    assert result["data"][CONF_DOSAGE_UNIT] == "each"


async def test_syrup_medication_full_flow(hass: HomeAssistant):
    """Test full config flow with syrup medication type."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Step 1: Medication details with syrup type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MEDICATION_NAME: "Cough Syrup",
            CONF_DOSAGE: "15",
            CONF_MEDICATION_TYPE: "syrup",
            CONF_DOSAGE_UNIT: "mL",
        },
    )

    # Step 2: Schedule type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TYPE: "fixed_time",
        },
    )

    # Step 3: Fixed time schedule
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCHEDULE_TIMES: ["20:00"],
            CONF_SCHEDULE_DAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        },
    )

    # Step 4: Refill settings - this should create the entry
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFILL_AMOUNT: 200,
            CONF_REFILL_REMINDER_DAYS: 5,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Cough Syrup"
    assert result["data"][CONF_MEDICATION_TYPE] == "syrup"
    assert result["data"][CONF_DOSAGE_UNIT] == "mL"
