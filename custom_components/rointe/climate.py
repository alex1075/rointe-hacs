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
from .const import DOMAIN
from .ws import SIGNAL_UPDATE
from .api import RointeAPI

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT]
PRESET_MODES = [PRESET_ECO, PRESET_COMFORT]

MIN_TEMP = 5.0
MAX_TEMP = 35.0

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Rointe climate entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    ws = data["ws"]
    api: RointeAPI = data["api"]
    devices = data["devices"]

    entities = []
    for dev in devices:
        entity = RointeHeater(hass, ws, api, dev["id"], dev.get("name", "Heater"), dev)
        entities.append(entity)

    async_add_entities(entities)


class RointeHeater(ClimateEntity):
    """Representation of a Rointe heater."""

    def __init__(self, hass, ws, api: RointeAPI, device_id: str, name: str, device_info: Optional[Dict[str, Any]]):
        self.hass = hass
        self.ws = ws
        self.api = api
        self.device_id = device_id
        self._attr_name = name
        self._attr_unique_id = f"rointe_{device_id}"
        self._attr_icon = "mdi:radiator"
        self._attr_hvac_modes = HVAC_MODES
        self._attr_preset_modes = PRESET_MODES
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 0.5
        self._attr_min_temp = MIN_TEMP
        self._attr_max_temp = MAX_TEMP
        self._attr_precision = 0.5
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_current_temperature = 20.0  # Default value so HA shows temp controls
        self._attr_target_temperature = 21.0   # Default value so HA shows temp controls
        self._attr_preset_mode = PRESET_ECO
        self._attr_hvac_action = HVACAction.OFF

        async_dispatcher_connect(hass, f"{SIGNAL_UPDATE}_{self.device_id}", self._handle_update)

    @property
    def current_temperature(self) -> Optional[float]:
        """Return current temperature."""
        return self._attr_current_temperature

    @property
    def target_temperature(self) -> Optional[float]:
        """Return target temperature."""
        return self._attr_target_temperature

    @property
    def min_temp(self) -> float:
        """Return minimum temperature."""
        return self._attr_min_temp

    @property
    def max_temp(self) -> float:
        """Return maximum temperature."""
        return self._attr_max_temp

    def _handle_update(self, state: dict):
        """Handle updates from WebSocket."""
        _LOGGER.debug("WS update for %s: %s", self.device_id, state)
        if "temp" in state:
            self._attr_current_temperature = state["temp"]
        if "um_max_temp" in state:
            self._attr_target_temperature = state["um_max_temp"]
        if "status" in state:
            if state["status"] == "comfort":
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_preset_mode = PRESET_COMFORT
                self._attr_hvac_action = HVACAction.HEATING
            elif state["status"] == "eco":
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_preset_mode = PRESET_ECO
                self._attr_hvac_action = HVACAction.HEATING
            elif state["status"] == "ice":
                self._attr_hvac_mode = HVACMode.OFF
                self._attr_preset_mode = None
                self._attr_hvac_action = HVACAction.OFF
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str):
        await self.api.set_hvac_mode(self.device_id, hvac_mode)
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_turn_on(self):
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_preset_mode(self, preset_mode: str):
        await self.api.set_preset_mode(self.device_id, preset_mode)
        self._attr_preset_mode = preset_mode
        self._attr_hvac_mode = HVACMode.HEAT
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.api.set_temperature(self.device_id, temperature)
        self._attr_target_temperature = temperature
        self.async_write_ha_state()