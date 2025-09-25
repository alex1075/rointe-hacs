import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_ECO,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .ws import SIGNAL_UPDATE

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_ECO]

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data["rointe"][entry.entry_id]
    ws = data["ws"]
    devices = data["devices"]

    entities = []
    for dev in devices:
        entities.append(RointeHeater(hass, ws, dev["id"], f"{dev['zone']} - {dev['name']}"))
    async_add_entities(entities)

class RointeHeater(ClimateEntity):
    def __init__(self, hass, ws, device_id, name):
        self.hass = hass
        self.ws = ws
        self.device_id = device_id
        self._name = name
        self._hvac_mode = HVAC_MODE_OFF
        self._current_temp = None
        self._target_temp = None
        async_dispatcher_connect(hass, SIGNAL_UPDATE, self._handle_update)

    @property
    def name(self): return self._name
    @property
    def supported_features(self): return SUPPORT_TARGET_TEMPERATURE
    @property
    def temperature_unit(self): return TEMP_CELSIUS
    @property
    def hvac_modes(self): return HVAC_MODES
    @property
    def hvac_mode(self): return self._hvac_mode
    @property
    def current_temperature(self): return self._current_temp
    @property
    def target_temperature(self): return self._target_temp

    def _handle_update(self, device_id, state):
        if device_id != self.device_id: return
        if "temp" in state: self._current_temp = state["temp"]
        if "um_max_temp" in state: self._target_temp = state["um_max_temp"]
        if "status" in state:
            if state["status"] == "comfort": self._hvac_mode = HVAC_MODE_HEAT
            elif state["status"] == "eco": self._hvac_mode = HVAC_MODE_ECO
            elif state["status"] == "ice": self._hvac_mode = HVAC_MODE_OFF
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        updates = {}
        if hvac_mode == HVAC_MODE_HEAT: updates = {"status": "comfort", "power": 2}
        elif hvac_mode == HVAC_MODE_ECO: updates = {"status": "eco", "power": 2}
        elif hvac_mode == HVAC_MODE_OFF: updates = {"status": "ice", "power": 1, "temp": 7}
        await self.ws.send(self.device_id, updates)
        self._hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            updates = {"um_max_temp": temp}
            await self.ws.send(self.device_id, updates)
            self._target_temp = temp
            self.async_write_ha_state()