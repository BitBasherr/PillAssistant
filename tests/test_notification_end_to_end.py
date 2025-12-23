"""End-to-end test for automatic notifications and mobile app action handling."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import (
    DOMAIN,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_DOSAGE_UNIT,
    CONF_SCHEDULE_TYPE,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_DAYS,
    CONF_REFILL_AMOUNT,
    CONF_REFILL_REMINDER_DAYS,
    CONF_NOTIFY_SERVICES,
)
from custom_components.pill_assistant import SIGNAL_MEDICATION_UPDATED


async def test_notification_and_action_flow(hass: "HomeAssistant"):
    """Test that automatic notification is sent and mobile action marks med taken."""
    now = dt_util.now()
    # Schedule a medication within the next 5 minutes to trigger 'due' immediately
    schedule_time = (now + timedelta(minutes=5)).strftime("%H:%M")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Notif_Med",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: [schedule_time],
            CONF_SCHEDULE_DAYS: [now.strftime("%a").lower()[:3]],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTIFY_SERVICES: ["notify.mobile_app_test_device"],
        },
    )

    entry.add_to_hass(hass)

    # Patch the notify service async_call to capture notifications
    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as mock_call:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # A notification should have been sent to the configured notify service
        assert mock_call.called, "Expected notify service to be called"

        # Inspect the call to ensure it targeted the notify domain/service
        called = False
        for call_args in mock_call.call_args_list:
            domain = call_args.args[0]
            service = call_args.args[1]
            if domain == "notify" and service.startswith("mobile_app"):
                called = True
                # Inspect payload contains tag/actions
                service_data = call_args.args[2]
                assert "data" in service_data
                assert "actions" in service_data["data"]
                assert any(
                    a["action"].startswith("take_medication_")
                    for a in service_data["data"]["actions"]
                )
        assert called, "Notify mobile app call not found in service calls"

        # Simulate user pressing the 'Mark as Taken' action in the mobile app
        hass.bus.async_fire(
            "mobile_app_notification_action",
            {"action": f"take_medication_{entry.entry_id}"},
        )
        await hass.async_block_till_done()

    # Verify medication was marked as taken in storage
    store = hass.data[DOMAIN][entry.entry_id]["store"]
    storage_data = await store.async_load()
    med_data = storage_data["medications"][entry.entry_id]
    assert (
        med_data["last_taken"] is not None
    ), "Medication should have last_taken set after action"


async def test_notification_dedup_same_occurrence(hass: "HomeAssistant"):
    """Test duplicate notifications for the same scheduled occurrence are suppressed."""
    now = dt_util.now()
    schedule_time = (now + timedelta(minutes=5)).strftime("%H:%M")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MEDICATION_NAME: "Notif_Med_Dedupe",
            CONF_DOSAGE: "1",
            CONF_DOSAGE_UNIT: "each",
            CONF_SCHEDULE_TYPE: "fixed_time",
            CONF_SCHEDULE_TIMES: [schedule_time],
            CONF_SCHEDULE_DAYS: [now.strftime("%a").lower()[:3]],
            CONF_REFILL_AMOUNT: 30,
            CONF_REFILL_REMINDER_DAYS: 7,
            CONF_NOTIFY_SERVICES: ["notify.mobile_app_test_device"],
        },
    )

    entry.add_to_hass(hass)

    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as mock_call:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Initial notify call should be present
        assert mock_call.call_count >= 1

        # Fire a global medication updated signal which will cause sensors to re-evaluate
        from homeassistant.helpers.dispatcher import async_dispatcher_send

        async_dispatcher_send(hass, SIGNAL_MEDICATION_UPDATED)
        await hass.async_block_till_done()

        # No additional notify call for the same scheduled occurrence
        assert (
            mock_call.call_count == 1
        ), "Duplicate notification was sent for same occurrence"
