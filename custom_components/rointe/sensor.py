"""Support for Rointe energy and temperature sensors."""
import logging
from typing import Optional, Dict, Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    SensorEntityDescription,
)
from homeassistant.const import (
    UnitOfPower,
    UnitOfEnergy,
    UnitOfTemperature,
    ATTR_DEVICE_CLASS,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import (
    DOMAIN,
    SENSOR_TYPE_POWER,
    SENSOR_TYPE_ENERGY,
    SENSOR_TYPE_CURRENT_TEMP,
    DEVICE_MODELS,
)
from .ws import SIGNAL_UPDATE

_LOGGER = logging.getLogger(__name__)

# Sensor descriptions
SENSOR_TYPES = {
    SENSOR_TYPE_POWER: SensorEntityDescription(
        key=SENSOR_TYPE_POWER,
        name="Power Consumption",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash",
    ),
    SENSOR_TYPE_ENERGY: SensorEntityDescription(
        key=SENSOR_TYPE_ENERGY,
        name="Energy Consumption",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:lightning-bolt",
    ),
    SENSOR_TYPE_CURRENT_TEMP: SensorEntityDescription(
        key=SENSOR_TYPE_CURRENT_TEMP,
        name="Current Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
    ),
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Rointe sensors from a config entry."""
    _LOGGER.debug("Setting up Rointe sensors for entry: %s", entry.entry_id)
    
    # Get the API
    api = hass.data[DOMAIN][entry.entry_id].get("api")
    
    if not api:
        _LOGGER.error("API not available for sensor setup")
        return
    
    # Get devices from API
    try:
        devices = await api.list_devices()
        _LOGGER.debug("Found %d devices for sensor setup", len(devices))
    except Exception as e:
        _LOGGER.error("Failed to get devices for sensor setup: %s", e)
        return
    
    entities = []
    
    for device_info in devices:
        device_id = device_info.get("id")
        device_name = device_info.get("name", f"Rointe {device_id}")
        device_model = device_info.get("model", "Unknown")
        device_type = device_info.get("type", "Unknown")
        
        # Determine device type from model
        device_category = None
        for model_key, category in DEVICE_MODELS.items():
            if model_key.lower() in device_model.lower():
                device_category = category
                break
        
        if not device_category:
            device_category = "radiator"  # Default
        
        _LOGGER.debug("Setting up sensors for device %s (%s) - Model: %s, Type: %s", 
                     device_id, device_name, device_model, device_category)
        
        # Create sensors for each device
        for sensor_type, description in SENSOR_TYPES.items():
            # Only create power/energy sensors for devices that support them
            if sensor_type in [SENSOR_TYPE_POWER, SENSOR_TYPE_ENERGY]:
                if device_category not in ["radiator", "towel_rail", "oval_towel"]:
                    continue  # Skip power sensors for thermostats
            
            entity = RointeSensor(
                api=api,
                device_info=device_info,
                sensor_type=sensor_type,
                description=description,
            )
            entities.append(entity)
    
    _LOGGER.info("Created %d sensor entities", len(entities))
    async_add_entities(entities, True)


class RointeSensor(Entity, SensorEntity):
    """Representation of a Rointe sensor."""
    
    def __init__(
        self,
        api,
        device_info: Dict[str, Any],
        sensor_type: str,
        description: SensorEntityDescription,
    ):
        """Initialize the sensor."""
        super().__init__()
        
        self._api = api
        self._device_info = device_info
        self._sensor_type = sensor_type
        self.entity_description = description
        
        # Device info
        self._device_id = device_info.get("id")
        self._device_name = device_info.get("name", f"Rointe {self._device_id}")
        self._device_model = device_info.get("model", "Unknown")
        self._device_power = device_info.get("power")
        
        # Sensor state
        self._state = None
        self._last_update = None
        self._energy_total = 0.0  # For energy consumption tracking
        
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
            "sw_version": device_info.get("version"),
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
            # Update sensor state based on type
            if self._sensor_type == SENSOR_TYPE_POWER:
                # Current power consumption in watts
                current_power = data.get("power", 0)
                if current_power and isinstance(current_power, (int, float)):
                    self._state = float(current_power)
                else:
                    # Estimate power based on device status and rated power
                    status = data.get("status", "off")
                    if status in ["comfort", "eco"] and self._device_power:
                        # Estimate current power (comfort = 100%, eco = 60%)
                        power_factor = 1.0 if status == "comfort" else 0.6
                        self._state = float(self._device_power) * power_factor
                    else:
                        self._state = 0.0
            
            elif self._sensor_type == SENSOR_TYPE_ENERGY:
                # Energy consumption in kWh
                energy_consumption = data.get("energyConsumption", 0)
                if energy_consumption and isinstance(energy_consumption, (int, float)):
                    self._state = float(energy_consumption) / 1000.0  # Convert to kWh
                else:
                    # Estimate energy based on current power
                    current_power = data.get("power", 0)
                    if current_power and isinstance(current_power, (int, float)):
                        # Simple estimation: power * time (assuming 1 hour)
                        self._energy_total += float(current_power) / 1000.0  # Convert to kWh
                        self._state = self._energy_total
            
            elif self._sensor_type == SENSOR_TYPE_CURRENT_TEMP:
                # Current temperature
                temperature = data.get("temperature")
                if temperature and isinstance(temperature, (int, float)):
                    self._state = float(temperature)
            
            self._last_update = data.get("timestamp")
            self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error("Error updating sensor %s: %s", self._attr_unique_id, e)
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            "device_id": self._device_id,
            "device_model": self._device_model,
            "sensor_type": self._sensor_type,
            "last_update": self._last_update,
        }
        
        if self._device_power:
            attrs["rated_power"] = self._device_power
        
        return attrs
    
    @property
    def available(self):
        """Return if entity is available."""
        return self._state is not None
