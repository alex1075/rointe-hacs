import logging
from typing import Optional, Dict, Any
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
    PRESET_ECO,
    PRESET_COMFORT,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, DEVICE_MODELS
from .ws import SIGNAL_UPDATE

_LOGGER = logging.getLogger(__name__)

# Rointe supports OFF and HEAT modes
HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT]

# Rointe preset modes
PRESET_MODES = [PRESET_ECO, PRESET_COMFORT]

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
    _LOGGER.error("🌡️🌡️🌡️ CLIMATE platform setup STARTING for entry: %s", entry.entry_id)
    try:
        data = hass.data[DOMAIN][entry.entry_id]
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
            _LOGGER.error("🔥🔥🔥 About to add %d entities to HA", len(entities))
            for entity in entities:
                _LOGGER.error("🔥🔥🔥 Entity details: %s, unique_id: %s, available: %s", 
                             entity.name, entity.unique_id, entity.available)
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
        """Initialize the Rointe heater entity."""
        self.hass = hass
        self.ws = ws
        self.device_id = device_id
        self._device_info = device_info or {}
        
        # Set entity attributes directly - this is the modern HA way
        self._attr_name = name
        self._attr_unique_id = f"rointe_{device_id}"
        self._attr_icon = "mdi:radiator"
        self._attr_has_entity_name = True
        self._attr_should_poll = False
        self._attr_available = True
        
        # Climate-specific attributes - CRITICAL for temperature controls
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._attr_preset_modes = [PRESET_ECO, PRESET_COMFORT]
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | 
            ClimateEntityFeature.PRESET_MODE |
            ClimateEntityFeature.TURN_ON |
            ClimateEntityFeature.TURN_OFF
        )
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 0.5
        self._attr_min_temp = 7.0
        self._attr_max_temp = 30.0
        self._attr_precision = 0.5
        
        # Set current state - CRITICAL for temperature controls to appear
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_current_temperature = 20.0
        self._attr_target_temperature = 21.0
        self._attr_preset_mode = PRESET_ECO
        self._attr_hvac_action = HVACAction.OFF
        
        # For backwards compatibility
        self._attr_hvac_mode = HVACMode.OFF
        self._current_temp = 20.0
        self._target_temp = 21.0
        self._available = True
        self._last_update_time = None
        
        # Device information
        self._device_model: Optional[str] = self._device_info.get("model")
        self._device_power: Optional[int] = self._device_info.get("power")
        self._device_version: Optional[str] = self._device_info.get("version")
        self._device_type: Optional[str] = self._device_info.get("type")
        self._device_serial: Optional[str] = self._device_info.get("serialNumber")
        self._device_mac: Optional[str] = self._device_info.get("mac")
        self._zone_name: Optional[str] = self._device_info.get("zone")
        
        # Determine device category from model
        self._device_category = None
        if self._device_model:
            for model_key, category in DEVICE_MODELS.items():
                if model_key.lower() in self._device_model.lower():
                    self._device_category = category
                    break
        if not self._device_category:
            self._device_category = "radiator"  # Default
        
        # Device status tracking
        self._device_status = self._device_info.get("deviceStatus", {})
        self._online = self._device_info.get("online", True)
        self._last_seen = self._device_info.get("lastSeen")
        
        # Connect to WebSocket updates
        async_dispatcher_connect(hass, f"{SIGNAL_UPDATE}_{self.device_id}", self._handle_update)
        
        _LOGGER.error("🔥🔥🔥 RointeHeater entity created with _attr_ attributes: %s (ID: %s)", name, self.device_id)
        _LOGGER.error("🔥🔥🔥 Entity attributes: hvac_modes=%s, supported_features=%s, temp_unit=%s", 
                     self._attr_hvac_modes, self._attr_supported_features, self._attr_temperature_unit)
        _LOGGER.error("🔥🔥🔥 Current state: hvac_mode=%s, current_temp=%s, target_temp=%s", 
                     self._attr_hvac_mode, self._attr_current_temperature, self._attr_target_temperature)

    async def async_added_to_hass(self):
        """Called when entity is added to Home Assistant."""
        _LOGGER.error("🔥🔥🔥 async_added_to_hass called for entity: %s", self._name)
        # Force HA to recognize this as a proper climate entity
        self.schedule_update_ha_state()
        
    async def async_update(self):
        """Update entity state."""
        _LOGGER.error("🔥🔥🔥 async_update called for entity: %s", self._name)
        # This method is called by HA to update the entity
        pass

    # Name is now handled by _attr_name = None (entity_name)

    @property
    def unique_id(self) -> str:
        """Return unique ID for this entity."""
        _LOGGER.error("🔥🔥🔥 unique_id property called: returning %s", f"rointe_{self.device_id}")
        return f"rointe_{self.device_id}"

    # Properties are now handled by _attr_ attributes for better HA compatibility

    @property
    def hvac_mode(self) -> str:
        """Return current HVAC mode."""
        return self._attr_hvac_mode
    
    @property
    def hvac_action(self) -> str:
        """Return current HVAC action."""
        if self._attr_hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        else:
            return HVACAction.HEATING

    @property
    def preset_mode(self) -> Optional[str]:
        """Return current preset mode."""
        if self._attr_hvac_mode == HVACMode.HEAT:
            # Map to comfort mode for heat
            return PRESET_COMFORT
        return None


    # current_temperature and target_temperature are now handled by _attr_ attributes

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        _LOGGER.error("🔥🔥🔥 name property called: returning %s", self._attr_name)
        return self._attr_name

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature for current HVAC mode."""
        mode_config = MODE_TEMPERATURES.get(self._attr_hvac_mode, MODE_TEMPERATURES[HVACMode.HEAT])
        return mode_config["min"]

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature for current HVAC mode."""
        mode_config = MODE_TEMPERATURES.get(self._attr_hvac_mode, MODE_TEMPERATURES[HVACMode.HEAT])
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
            "name": self._attr_name,
            "manufacturer": "Rointe",
            "model": self._device_model or "Rointe Heater",
        }
        
        if self._device_version:
            info["sw_version"] = self._device_version
        
        if self._device_serial:
            info["serial_number"] = self._device_serial
        
        if self._zone_name:
            info["suggested_area"] = self._zone_name
        
        return info

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "device_id": self.device_id,
            "device_category": self._device_category,
            "online": self._online,
        }
        
        if self._device_power:
            attrs["power_watts"] = self._device_power
        
        if self._device_model:
            attrs["device_model"] = self._device_model
        
        if self._device_version:
            attrs["device_version"] = self._device_version
        
        if self._device_type:
            attrs["device_type"] = self._device_type
        
        if self._device_serial:
            attrs["serial_number"] = self._device_serial
        
        if self._device_mac:
            attrs["mac_address"] = self._device_mac
        
        if self._zone_name:
            attrs["zone"] = self._zone_name
        
        if self._last_seen:
            attrs["last_seen"] = self._last_seen
        
        if self._last_update_time:
            attrs["last_update"] = self._last_update_time.isoformat()
        
        if self._device_status:
            attrs["device_status"] = self._device_status
        
        return attrs

    def _handle_update(self, state: dict):
        """Handle WebSocket updates."""
        
        try:
            _LOGGER.debug("Received update for device %s: %s", self.device_id, state)
            
            # Update device status information
            self._device_status = state.get("deviceStatus", self._device_status)
            self._online = state.get("online", self._online)
            self._last_seen = state.get("lastSeen", self._last_seen)
            
            # Update current temperature
            if "temp" in state and isinstance(state["temp"], (int, float)):
                temp = float(state["temp"])
                if MIN_TEMP <= temp <= MAX_TEMP:
                    self._current_temp = temp
                    self._attr_current_temperature = temp  # Sync to _attr_ for HA
                else:
                    _LOGGER.warning("Temperature %s out of range for device %s", temp, self.device_id)
            
            # Update target temperature - check both possible keys
            target_temp = None
            if "um_max_temp" in state and isinstance(state["um_max_temp"], (int, float)):
                target_temp = float(state["um_max_temp"])
            elif "temp" in state and isinstance(state["temp"], (int, float)):
                # If "temp" is the target temperature (not current)
                target_temp = float(state["temp"])
            
            if target_temp is not None and MIN_TEMP <= target_temp <= MAX_TEMP:
                self._target_temp = target_temp
                self._attr_target_temperature = target_temp  # Sync to _attr_ for HA
            elif target_temp is not None:
                _LOGGER.warning("Target temperature %s out of range for device %s", target_temp, self.device_id)
            
            # Update HVAC mode and preset based on device status
            if "status" in state and isinstance(state["status"], str):
                status = state["status"].lower()
                if status == "comfort":
                    self._attr_hvac_mode = HVACMode.HEAT
                    self._attr_hvac_mode = HVACMode.HEAT
                    self._attr_preset_mode = PRESET_COMFORT
                    self._attr_hvac_action = HVACAction.HEATING
                elif status == "eco":
                    self._attr_hvac_mode = HVACMode.HEAT
                    self._attr_hvac_mode = HVACMode.HEAT
                    self._attr_preset_mode = PRESET_ECO
                    self._attr_hvac_action = HVACAction.HEATING
                elif status == "ice":
                    self._attr_hvac_mode = HVACMode.OFF
                    self._attr_hvac_mode = HVACMode.OFF
                    self._attr_preset_mode = None
                    self._attr_hvac_action = HVACAction.OFF
                else:
                    _LOGGER.warning("Unknown status '%s' for device %s", status, self.device_id)
            
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
            _LOGGER.error("Error handling update for device %s: %s", self.device_id, e)

    async def async_set_hvac_mode(self, hvac_mode: str):
        """Set new HVAC mode."""
        if hvac_mode not in HVAC_MODES:
            _LOGGER.error("Invalid HVAC mode: %s", hvac_mode)
            return
        
        try:
            updates = {}
            if hvac_mode == HVACMode.HEAT:
                # Use "comfort" mode for HEAT (matches Rointe website behavior)
                updates = {"status": "comfort", "power": 2}
            elif hvac_mode == HVACMode.OFF:
                # For OFF mode, we can use either "ice" or "eco" - let's use "eco" for standby
                updates = {"status": "eco", "power": 1}
            
            _LOGGER.info("🔥 HVAC MODE CHANGE: Setting mode %s for device %s: %s", hvac_mode, self.device_id, updates)
            await self.ws.send(self.device_id, updates)
            _LOGGER.info("🔥 HVAC mode command sent successfully!")
            
            # Optimistically update local state and sync to _attr_ for HA
            self._attr_hvac_mode = hvac_mode
            self._attr_hvac_mode = hvac_mode
            
            # Update preset mode and action based on HVAC mode
            if hvac_mode == HVACMode.HEAT:
                self._attr_preset_mode = PRESET_COMFORT
                self._attr_hvac_action = HVACAction.HEATING
            elif hvac_mode == HVACMode.OFF:
                self._attr_preset_mode = None
                self._attr_hvac_action = HVACAction.OFF
            
            self.async_write_ha_state()
            _LOGGER.info("🔥 Local HVAC mode updated to %s", self._attr_hvac_mode)
            
        except Exception as e:
            _LOGGER.error("Error setting HVAC mode %s for device %s: %s", hvac_mode, self.device_id, e)
            self._available = False
            self.async_write_ha_state()
            raise RointeDeviceError(f"Failed to set HVAC mode: {e}")

    async def async_turn_on(self):
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_preset_mode(self, preset_mode: str):
        """Set new target preset mode."""
        _LOGGER.info("🔥 PRESET MODE CHANGE: Setting preset %s for device %s", preset_mode, self.device_id)
        
        try:
            updates = {}
            if preset_mode == PRESET_COMFORT:
                updates = {"status": "comfort", "power": 2}
            elif preset_mode == PRESET_ECO:
                updates = {"status": "eco", "power": 1}
            
            _LOGGER.info("🔥 Preset updates to send: %s", updates)
            await self.ws.send(self.device_id, updates)
            _LOGGER.info("🔥 Preset command sent successfully!")
            
            # Update local state and sync to _attr_ for HA
            self._attr_preset_mode = preset_mode
            if preset_mode in [PRESET_COMFORT, PRESET_ECO]:
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_hvac_action = HVACAction.HEATING
            else:
                self._attr_hvac_mode = HVACMode.OFF
                self._attr_hvac_mode = HVACMode.OFF
                self._attr_hvac_action = HVACAction.OFF
            
            self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error("❌ ERROR setting preset mode %s for device %s: %s", preset_mode, self.device_id, e)
            raise RointeDeviceError(f"Failed to set preset mode: {e}")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
            
        _LOGGER.error("🔥🔥🔥 async_set_temperature called with temperature: %s", temperature)
        
        # Validate temperature range
        if not (self.min_temp <= temperature <= self.max_temp):
            _LOGGER.warning("Temperature %s outside valid range %s-%s for device %s", 
                          temperature, self.min_temp, self.max_temp, self.device_id)
            return
        
        # Update target temperature
        self._target_temp = temperature
        self._attr_target_temperature = temperature  # Sync to _attr_ for HA
        
        # Send temperature update to device
        # Try "temp" first (from WebSocket captures), fallback to "um_max_temp"
        updates = {"temp": temperature}
        await self.ws.send(self.device_id, updates)
        
        _LOGGER.error("🔥🔥🔥 Temperature set to %s, current: %s, target: %s", 
                     temperature, self._current_temp, self._target_temp)
        
        self.schedule_update_ha_state()