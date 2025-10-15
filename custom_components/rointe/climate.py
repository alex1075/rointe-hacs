import logging
from typing import Optional, Dict, Any
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    ATTR_HVAC_MODE,
)

# Define preset modes
try:
    from homeassistant.components.climate import PRESET_COMFORT, PRESET_ECO
except ImportError:
    PRESET_COMFORT = "comfort"
    PRESET_ECO = "eco"

PRESET_ICE = "ice"

# Rointe mode mappings
ROINTE_MODES = {
    "comfort": {"status": "comfort", "power": 2},
    "eco": {"status": "eco", "power": 2},
    "ice": {"status": "ice", "power": 2, "temp": 7},
}

PRESET_TO_ROINTE = {
    PRESET_COMFORT: "comfort",
    PRESET_ECO: "eco",
    PRESET_ICE: "ice",
}

ROINTE_TO_PRESET = {
    "comfort": PRESET_COMFORT,
    "eco": PRESET_ECO,
    "ice": PRESET_ICE,
    "none": PRESET_COMFORT,
}

from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, DEVICE_MODELS
from .ws import SIGNAL_UPDATE
from .api import *

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT]

MIN_TEMP = 5.0
MAX_TEMP = 35.0

class RointeDeviceError(Exception):
    """Error communicating with Rointe device."""
    pass

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Rointe climate entities."""
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
                zone_id = dev.get("zone_id")
                
                _LOGGER.debug("Device dict keys: %s", dev.keys())
                
                if not device_id:
                    _LOGGER.error("Device missing ID: %s", dev)
                    continue
                
                _LOGGER.debug("Device %s has zone_id: %s (zone_name: %s)", device_id, zone_id, zone_name)
                
                entity_name = f"{zone_name} - {device_name}"
                entity = RointeHeater(
                    api=hass.data[DOMAIN][entry.entry_id]["api"], 
                    hass=hass, 
                    ws=ws,
                    device_id=device_id,
                    name=entity_name, 
                    device_info=dev
                )
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
    """Representation of a Rointe heater with preset modes."""

    def __init__(self, hass, ws, api, device_id: str, name: str, device_info: Optional[Dict[str, Any]] = None):
        self.hass = hass
        self.ws = ws
        self.api = api
        self.device_id = device_id
        self._name = name
        self._device_info = device_info or {}
        self._hvac_mode = HVACMode.OFF
        self._preset_mode = PRESET_COMFORT
        self._current_temp: Optional[float] = None
        self._target_temp: Optional[float] = None
        self._available = True
        self._last_update_time = None
        self._schedule_mode = False  # mode: 0=manual, 1=schedule
        
        # Device information
        self._device_model: Optional[str] = self._device_info.get("model")
        self._device_power: Optional[int] = self._device_info.get("power")
        self._device_version: Optional[str] = self._device_info.get("version")
        self._device_type: Optional[str] = self._device_info.get("type")
        self._device_serial: Optional[str] = self._device_info.get("serialNumber")
        self._device_mac: Optional[str] = self._device_info.get("mac")
        self._zone_name: Optional[str] = self._device_info.get("zone")
        self._zone_id: Optional[str] = self._device_info.get("zone_id")
        
        _LOGGER.debug("Initialized device %s with zone_id: %s", device_id, self._zone_id)
        
        # Determine device category from model
        self._device_category = None
        if self._device_model:
            for model_key, category in DEVICE_MODELS.items():
                if model_key.lower() in self._device_model.lower():
                    self._device_category = category
                    break
        if not self._device_category:
            self._device_category = "radiator"
        
        # Device status tracking
        self._device_status = self._device_info.get("deviceStatus", {})
        self._online = self._device_info.get("online", True)
        self._last_seen = self._device_info.get("lastSeen")
        
        # Connect to WebSocket updates
        async_dispatcher_connect(hass, f"{SIGNAL_UPDATE}_{self.device_id}", self._handle_update)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE

    @property
    def preset_modes(self):
        """Return available preset modes."""
        return [PRESET_COMFORT, PRESET_ECO, PRESET_ICE]

    @property
    def preset_mode(self):
        """Return current preset mode."""
        return self._preset_mode

    @property
    def name(self) -> str:
        """Return the name of the climate entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID for this entity."""
        return f"rointe_{self.device_id}"

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
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return MAX_TEMP

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
            "schedule_mode": "Schedule" if self._schedule_mode else "Manual",
        }
        
        if self._device_power:
            attrs["power_watts"] = self._device_power
        
        if self._zone_id:
            attrs["zone_id"] = self._zone_id
        
        return attrs

    def _handle_update(self, state: dict):
        """Handle WebSocket updates."""
        
        try:
            _LOGGER.debug("Received update for device %s: %s", self.device_id, state)
            
            # Update device status
            self._device_status = state.get("deviceStatus", self._device_status)
            self._online = state.get("online", self._online)
            self._last_seen = state.get("lastSeen", self._last_seen)
            
            # Update schedule mode
            if "mode" in state:
                self._schedule_mode = (state["mode"] == 1)
            
            # Update current temperature
            if "temp" in state and isinstance(state["temp"], (int, float)):
                temp = float(state["temp"])
                if MIN_TEMP <= temp <= MAX_TEMP:
                    self._current_temp = temp
            
            # Update target temperature from multiple possible fields
            for temp_field in ["temp", "comfort", "eco", "ice"]:
                if temp_field in state and isinstance(state[temp_field], (int, float)):
                    temp = float(state[temp_field])
                    if MIN_TEMP <= temp <= MAX_TEMP:
                        self._target_temp = temp
                        break
            
            # Update mode and preset based on status and power
            if "status" in state:
                status = state["status"].lower()
                power = state.get("power", 1)
                
                # Map status to preset
                self._preset_mode = ROINTE_TO_PRESET.get(status, PRESET_COMFORT)
                
                # HVAC mode: OFF if power=1, otherwise HEAT
                if power == 1:
                    self._hvac_mode = HVACMode.OFF
                else:
                    self._hvac_mode = HVACMode.HEAT
            
            self._available = True
            self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error("Error handling update for device %s: %s", self.device_id, e)

    async def async_set_preset_mode(self, preset_mode: str):
        """Set new preset mode."""
        if preset_mode not in PRESET_TO_ROINTE:
            _LOGGER.error("Invalid preset mode: %s", preset_mode)
            return

        try:
            rointe_mode = PRESET_TO_ROINTE[preset_mode]
            updates = ROINTE_MODES[rointe_mode].copy()
            
            _LOGGER.debug("Setting preset %s for device %s: %s", preset_mode, self.device_id, updates)
            
            await self.ws.send(self._zone_id, self.device_id, updates)
            
            self._preset_mode = preset_mode
            self._hvac_mode = HVACMode.HEAT
            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.error("Error setting preset %s for device %s: %s", preset_mode, self.device_id, e)
            self._available = False
            self.async_write_ha_state()
            raise RointeDeviceError(f"Failed to set preset mode: {e}")

    async def async_set_hvac_mode(self, hvac_mode: str):
        """Set new HVAC mode."""
        if hvac_mode not in HVAC_MODES:
            _LOGGER.error("Invalid HVAC mode: %s", hvac_mode)
            return

        try:
            if hvac_mode == HVACMode.HEAT:
                # When turning on, use current preset or default to comfort
                rointe_mode = PRESET_TO_ROINTE.get(self._preset_mode, "comfort")
                updates = ROINTE_MODES[rointe_mode].copy()
            elif hvac_mode == HVACMode.OFF:
                # Standby mode - power:1, status changes to "none" automatically
                updates = {
                    "power": 1,
                    "temp": 7
                }

            _LOGGER.debug("Setting HVAC mode %s for device %s: %s", hvac_mode, self.device_id, updates)

            await self.ws.send(self._zone_id, self.device_id, updates)

            self._hvac_mode = hvac_mode
            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.error("Error setting HVAC mode %s for device %s: %s", hvac_mode, self.device_id, e)
            self._available = False
            self.async_write_ha_state()
            raise RointeDeviceError(f"Failed to set HVAC mode: {e}")

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature - changes temp within current preset."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        try:
            # Limit the target temperature
            if temperature < self.min_temp or temperature > self.max_temp:
                _LOGGER.warning('Temperature requested is outside min/max range, adjusting')
                temperature = min(self.max_temp, temperature)
                temperature = max(self.min_temp, temperature)
            
            # Send temperature change - device will handle mode switching
            updates = {
                "temp": int(temperature),
                "power": 2
            }
            
            _LOGGER.debug("Setting temperature %s for device %s", temperature, self.device_id)
            
            await self.ws.send(self._zone_id, self.device_id, updates)
            
            self._target_temp = temperature
            self._hvac_mode = HVACMode.HEAT
            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.error("Error setting temperature for device %s: %s", self.device_id, e)
            self._available = False
            self.async_write_ha_state()
            raise RointeDeviceError(f"Failed to set temperature: {e}")
