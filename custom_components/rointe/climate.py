import logging
from typing import Optional, Dict, Any
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .ws import SIGNAL_UPDATE

_LOGGER = logging.getLogger(__name__)

# Rointe only supports OFF and HEAT modes
HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT]

# Rointe device states map to HVAC modes
# comfort/eco -> HEAT mode, ice -> OFF mode

# Temperature limits for Rointe devices
MIN_TEMP = 5.0
MAX_TEMP = 35.0

# Mode-specific temperature ranges
MODE_TEMPERATURES = {
    HVACMode.OFF: {"min": 5.0, "max": 7.0, "default": 7.0},
    HVACMode.HEAT: {"min": 15.0, "max": 35.0, "default": 21.0},
}

class RointeDeviceError(Exception):
    """Error communicating with Rointe device."""
    pass

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Rointe climate entities."""
    try:
        data = hass.data["rointe"][entry.entry_id]
        ws = data["ws"]
        devices = data["devices"]

        if not devices:
            _LOGGER.warning("No devices found during setup")
            return

        entities = []
        for dev in devices:
            try:
                device_id = dev.get("id")
                device_name = dev.get("name", "Unknown Device")
                zone_name = dev.get("zone", "Unknown Zone")
                
                if not device_id:
                    _LOGGER.error("Device missing ID: %s", dev)
                    continue
                
                entity_name = f"{zone_name} - {device_name}"
                entity = RointeHeater(hass, ws, device_id, entity_name, dev)
                entities.append(entity)
                _LOGGER.debug("Created climate entity for device %s: %s", device_id, entity_name)
                
            except Exception as e:
                _LOGGER.error("Error creating entity for device %s: %s", dev, e)
                continue
        
        if entities:
            async_add_entities(entities, update_before_add=False)
            _LOGGER.info("Successfully set up %d Rointe climate entities", len(entities))
        else:
            _LOGGER.error("No valid climate entities created")
            
    except Exception as e:
        _LOGGER.error("Error setting up Rointe climate entities: %s", e)
        raise

class RointeHeater(ClimateEntity):
    """Representation of a Rointe heater with enhanced features."""

    def __init__(self, hass, ws, device_id: str, name: str, device_info: Optional[Dict[str, Any]] = None):
        self.hass = hass
        self.ws = ws
        self.device_id = device_id
        self._name = name
        self._device_info = device_info or {}
        self._hvac_mode = HVACMode.OFF
        self._current_temp: Optional[float] = None
        self._target_temp: Optional[float] = None
        self._available = True
        self._last_update_time = None
        self._device_model: Optional[str] = None
        self._device_power: Optional[int] = None
        self._device_version: Optional[str] = None
        
        # Connect to WebSocket updates
        async_dispatcher_connect(hass, SIGNAL_UPDATE, self._handle_update)

    @property
    def name(self) -> str:
        """Return the name of the climate entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID for this entity."""
        return f"rointe_{self.device_id}"

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return "°C"

    @property
    def hvac_modes(self):
        """Return the list of available HVAC modes."""
        return HVAC_MODES

    @property
    def hvac_mode(self) -> str:
        """Return current HVAC mode."""
        return self._hvac_mode


    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        return self._current_temp

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the target temperature."""
        return self._target_temp

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature for current HVAC mode."""
        mode_config = MODE_TEMPERATURES.get(self._hvac_mode, MODE_TEMPERATURES[HVACMode.HEAT])
        return mode_config["min"]

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature for current HVAC mode."""
        mode_config = MODE_TEMPERATURES.get(self._hvac_mode, MODE_TEMPERATURES[HVACMode.HEAT])
        return mode_config["max"]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information for Home Assistant."""
        info = {
            "identifiers": {("rointe", self.device_id)},
            "name": self._name,
            "manufacturer": "Rointe",
            "model": self._device_model or "Rointe Heater",
        }
        
        if self._device_version:
            info["sw_version"] = self._device_version
        
        return info

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "device_id": self.device_id,
        }
        
        if self._device_power:
            attrs["power_watts"] = self._device_power
        
        if self._device_model:
            attrs["device_model"] = self._device_model
        
        if self._device_version:
            attrs["device_version"] = self._device_version
        
        return attrs

    def _handle_update(self, device_id: str, state: dict):
        """Handle WebSocket updates."""
        if device_id != self.device_id:
            return
        
        try:
            _LOGGER.debug("Received update for device %s: %s", device_id, state)
            
            # Update current temperature
            if "temp" in state and isinstance(state["temp"], (int, float)):
                temp = float(state["temp"])
                if MIN_TEMP <= temp <= MAX_TEMP:
                    self._current_temp = temp
                else:
                    _LOGGER.warning("Temperature %s out of range for device %s", temp, device_id)
            
            # Update target temperature
            if "um_max_temp" in state and isinstance(state["um_max_temp"], (int, float)):
                temp = float(state["um_max_temp"])
                if MIN_TEMP <= temp <= MAX_TEMP:
                    self._target_temp = temp
                else:
                    _LOGGER.warning("Target temperature %s out of range for device %s", temp, device_id)
            
            # Update HVAC mode based on device status
            if "status" in state and isinstance(state["status"], str):
                status = state["status"].lower()
                if status in ["comfort", "eco"]:
                    self._hvac_mode = HVACMode.HEAT
                elif status == "ice":
                    self._hvac_mode = HVACMode.OFF
                else:
                    _LOGGER.warning("Unknown status '%s' for device %s", status, device_id)
            
            # Update device information if available
            if "model" in state and isinstance(state["model"], str):
                self._device_model = state["model"]
            
            if "power" in state and isinstance(state["power"], (int, float)):
                self._device_power = int(state["power"])
            
            if "version" in state and isinstance(state["version"], str):
                self._device_version = state["version"]
            
            # Mark as available
            self._available = True
            
            # Update state
            self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error("Error handling update for device %s: %s", device_id, e)

    async def async_set_hvac_mode(self, hvac_mode: str):
        """Set new HVAC mode."""
        if hvac_mode not in HVAC_MODES:
            _LOGGER.error("Invalid HVAC mode: %s", hvac_mode)
            return
        
        try:
            updates = {}
            if hvac_mode == HVACMode.HEAT:
                updates = {"status": "comfort", "power": 2}
            elif hvac_mode == HVACMode.OFF:
                updates = {"status": "ice", "power": 1, "temp": 7}
            
            _LOGGER.debug("Setting HVAC mode %s for device %s: %s", hvac_mode, self.device_id, updates)
            await self.ws.send(self.device_id, updates)
            
            # Optimistically update local state
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error("Error setting HVAC mode %s for device %s: %s", hvac_mode, self.device_id, e)
            self._available = False
            self.async_write_ha_state()
            raise RointeDeviceError(f"Failed to set HVAC mode: {e}")


    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            _LOGGER.warning("No temperature provided for device %s", self.device_id)
            return
        
        # Validate temperature
        if not isinstance(temp, (int, float)):
            _LOGGER.error("Invalid temperature type for device %s: %s", self.device_id, type(temp))
            raise ValueError(f"Temperature must be a number, got {type(temp)}")
        
        temp = float(temp)
        mode_config = MODE_TEMPERATURES.get(self._hvac_mode, MODE_TEMPERATURES[HVACMode.HEAT])
        min_temp = mode_config["min"]
        max_temp = mode_config["max"]
        
        if temp < min_temp or temp > max_temp:
            _LOGGER.error("Temperature %s out of range [%s, %s] for mode %s on device %s", 
                         temp, min_temp, max_temp, self._hvac_mode, self.device_id)
            raise ValueError(f"Temperature must be between {min_temp} and {max_temp} for {self._hvac_mode} mode")
        
        try:
            updates = {"um_max_temp": temp}
            _LOGGER.debug("Setting temperature %s for device %s", temp, self.device_id)
            await self.ws.send(self.device_id, updates)
            
            # Optimistically update local state
            self._target_temp = temp
            self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error("Error setting temperature %s for device %s: %s", temp, self.device_id, e)
            self._available = False
            self.async_write_ha_state()
            raise RointeDeviceError(f"Failed to set temperature: {e}")