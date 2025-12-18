"""Test Pill Assistant device info grouping."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import DOMAIN


async def test_sensor_has_device_info(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that sensor entity has device_info properly configured."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get the sensor entity
    entity_id = "sensor.pa_test_medication"
    state = hass.states.get(entity_id)
    assert state is not None

    # Get entity registry
    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get(entity_id)
    assert entity_entry is not None
    assert entity_entry.device_id is not None

    # Get device registry and verify device exists
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(entity_entry.device_id)
    assert device is not None
    assert device.name == "Pill Assistant - Test Medication"
    assert device.manufacturer == "Pill Assistant"
    assert device.model == "Medication Tracker"
    assert (DOMAIN, mock_config_entry.entry_id) in device.identifiers


async def test_button_has_device_info(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that button entity has device_info properly configured."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get the button entity
    entity_id = "button.pa_test_medication"
    state = hass.states.get(entity_id)
    assert state is not None

    # Get entity registry
    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get(entity_id)
    assert entity_entry is not None
    assert entity_entry.device_id is not None

    # Get device registry and verify device exists
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(entity_entry.device_id)
    assert device is not None
    assert device.name == "Pill Assistant - Test Medication"
    assert device.manufacturer == "Pill Assistant"
    assert device.model == "Medication Tracker"
    assert (DOMAIN, mock_config_entry.entry_id) in device.identifiers


async def test_sensor_and_button_share_same_device(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Test that sensor and button entities are grouped under the same device."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get entity registry
    ent_reg = er.async_get(hass)

    # Get sensor entity
    sensor_entity_id = "sensor.pa_test_medication"
    sensor_entry = ent_reg.async_get(sensor_entity_id)
    assert sensor_entry is not None
    assert sensor_entry.device_id is not None

    # Get button entity
    button_entity_id = "button.pa_test_medication"
    button_entry = ent_reg.async_get(button_entity_id)
    assert button_entry is not None
    assert button_entry.device_id is not None

    # Verify both entities share the same device
    assert sensor_entry.device_id == button_entry.device_id

    # Verify the device has both entities
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(sensor_entry.device_id)
    assert device is not None

    # Get all entities for this device
    device_entities = er.async_entries_for_device(ent_reg, sensor_entry.device_id)
    entity_ids = {entry.entity_id for entry in device_entities}

    assert sensor_entity_id in entity_ids
    assert button_entity_id in entity_ids
    assert len(device_entities) == 2  # Should have exactly 2 entities (sensor + button)
