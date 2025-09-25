"""Support for Rointe binary sensors (firmware updates)."""
import logging
from typing import Optional, Dict, Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import (
    DOMAIN,
    BINARY_SENSOR_TYPE_FIRMWARE_UPDATE,
)
from .ws import SIGNAL_UPDATE

_LOGGER = logging.getLogger(__name__)

# Binary sensor descriptions
BINARY_SENSOR_TYPES = {
    BINARY_SENSOR_TYPE_FIRMWARE_UPDATE: BinarySensorEntityDescription(
        key=BINARY_SENSOR_TYPE_FIRMWARE_UPDATE,
        name="Firmware Update Available",
        device_class=BinarySensorDeviceClass.UPDATE,
        icon="mdi:update",
    ),
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Rointe binary sensors from a config entry."""
    _LOGGER.debug("Setting up Rointe binary sensors for entry: %s", entry.entry_id)
    
    # Get the API
    api = hass.data[DOMAIN][entry.entry_id].get("api")
    
    if not api:
        _LOGGER.error("API not available for binary sensor setup")
        return
    
    # Get devices from API
    try:
        devices = await api.list_devices()
        _LOGGER.debug("Found %d devices for binary sensor setup", len(devices))
    except Exception as e:
        _LOGGER.error("Failed to get devices for binary sensor setup: %s", e)
        return
    
    entities = []
    
    for device_info in devices:
        device_id = device_info.get("id")
        device_name = device_info.get("name", f"Rointe {device_id}")
        device_model = device_info.get("model", "Unknown")
        device_version = device_info.get("version", "Unknown")
        
        _LOGGER.debug("Setting up binary sensors for device %s (%s) - Model: %s, Version: %s", 
                     device_id, device_name, device_model, device_version)
        
        # Create binary sensors for each device
        for sensor_type, description in BINARY_SENSOR_TYPES.items():
            entity = RointeBinarySensor(
                api=api,
                device_info=device_info,
                sensor_type=sensor_type,
                description=description,
            )
            entities.append(entity)
    
    _LOGGER.info("Created %d binary sensor entities", len(entities))
    async_add_entities(entities, True)


class RointeBinarySensor(Entity, BinarySensorEntity):
    """Representation of a Rointe binary sensor."""
    
    def __init__(
        self,
        api,
        device_info: Dict[str, Any],
        sensor_type: str,
        description: BinarySensorEntityDescription,
    ):
        """Initialize the binary sensor."""
        super().__init__()
        
        self._api = api
        self._device_info = device_info
        self._sensor_type = sensor_type
        self.entity_description = description
        
        # Device info
        self._device_id = device_info.get("id")
        self._device_name = device_info.get("name", f"Rointe {self._device_id}")
        self._device_model = device_info.get("model", "Unknown")
        self._device_version = device_info.get("version", "Unknown")
        
        # Sensor state
        self._state = False
        self._last_update = None
        self._update_info = {}
        
        # Unique ID
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_{sensor_type}"
        
        # Entity name
        self._attr_name = f"{self._device_name} {description.name}"
        
        # Device info for device registry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "Rointe",
            "model": self._device_model,
            "sw_version": self._device_version,
        }
    
    
    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        # Listen for WebSocket updates
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATE}_{self._device_id}",
                self._handle_update,
            )
        )
    
    @callback
    def _handle_update(self, data: Dict[str, Any]):
        """Handle WebSocket update."""
        if not data:
            return
        
        try:
            if self._sensor_type == BINARY_SENSOR_TYPE_FIRMWARE_UPDATE:
                # Check for firmware update availability
                firmware_update = data.get("firmwareUpdate")
                update_available = data.get("updateAvailable", False)
                latest_version = data.get("latestVersion")
                current_version = data.get("version", self._device_version)
                
                # Determine if update is available
                if firmware_update:
                    # Direct firmware update info
                    self._state = firmware_update.get("available", False)
                    self._update_info = firmware_update
                elif update_available or latest_version:
                    # Update available flag or version comparison
                    self._state = update_available
                    if latest_version and latest_version != current_version:
                        self._state = True
                        self._update_info = {
                            "current_version": current_version,
                            "latest_version": latest_version,
                            "available": True,
                        }
                else:
                    # Check for update indicators in device status
                    device_status = data.get("deviceStatus", {})
                    if isinstance(device_status, dict):
                        self._state = device_status.get("updateAvailable", False)
                        if self._state:
                            self._update_info = device_status.get("updateInfo", {})
                
                self._last_update = data.get("timestamp")
            
            self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error("Error updating binary sensor %s: %s", self._attr_unique_id, e)
    
    @property
    def is_on(self):
        """Return the state of the binary sensor."""
        return self._state
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            "device_id": self._device_id,
            "device_model": self._device_model,
            "current_version": self._device_version,
            "sensor_type": self._sensor_type,
            "last_update": self._last_update,
        }
        
        # Add firmware update specific attributes
        if self._sensor_type == BINARY_SENSOR_TYPE_FIRMWARE_UPDATE and self._update_info:
            attrs.update({
                "update_info": self._update_info,
                "update_available": self._state,
            })
            
            if "latest_version" in self._update_info:
                attrs["latest_version"] = self._update_info["latest_version"]
            
            if "current_version" in self._update_info:
                attrs["current_version"] = self._update_info["current_version"]
        
        return attrs
    
    @property
    def available(self):
        """Return if entity is available."""
        return True  # Binary sensors are always available
