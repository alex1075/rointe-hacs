"""Rointe switch platform for schedule mode control."""
import logging
from typing import Any, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .ws import SIGNAL_UPDATE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rointe switch entities."""
    rointe_data = hass.data[DOMAIN][config_entry.entry_id]
    ws = rointe_data["ws"]
    devices = rointe_data["devices"]

    entities = []
    for device in devices:
        device_id = device.get("id")
        zone_name = device.get("zone", "Unknown Zone")
        device_name = device.get("name", "Unknown Device")
        
        if device_id:
            entity = RointeScheduleSwitch(
                hass=hass,
                ws=ws,
                device_id=device_id,
                device_name=f"{zone_name} - {device_name}",
                device_info=device,
            )
            entities.append(entity)

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Set up %d Rointe schedule switches", len(entities))


class RointeScheduleSwitch(SwitchEntity):
    """Switch to control Rointe device schedule mode."""

    def __init__(
        self,
        hass: HomeAssistant,
        ws,
        device_id: str,
        device_name: str,
        device_info: dict,
    ):
        """Initialize the switch."""
        self.hass = hass
        self.ws = ws
        self._device_id = device_id
        self._device_name = device_name
        self._device_info = device_info
        self._zone_id = device_info.get("zone_id")
        self._is_on = False
        self._available = True

        # Connect to WebSocket updates
        async_dispatcher_connect(hass, f"{SIGNAL_UPDATE}_{self._device_id}", self._handle_update)

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"{self._device_name} Schedule"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"rointe_{self._device_id}_schedule"

    @property
    def is_on(self) -> bool:
        """Return true if schedule mode is enabled."""
        return self._is_on

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._available

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:calendar-clock" if self._is_on else "mdi:calendar-remove"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {("rointe", self._device_id)},
            "name": self._device_name,
            "manufacturer": "Rointe",
        }

    def _handle_update(self, state: dict):
        """Handle WebSocket updates."""
        try:
            _LOGGER.debug("Switch received update for device %s: %s", self._device_id, state)
            
            # Update schedule mode from WebSocket
            if "mode" in state:
                self._is_on = (state["mode"] == 1)
                self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error("Error handling switch update for device %s: %s", self._device_id, e)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on schedule mode."""
        try:
            updates = {"mode": 1, "power": 2}
            _LOGGER.debug("Enabling schedule mode for device %s", self._device_id)
            await self.ws.send(self._zone_id, self._device_id, updates)
            self._is_on = True
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to enable schedule mode: %s", e)
            self._available = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off schedule mode (manual mode)."""
        try:
            updates = {"mode": 0}
            _LOGGER.debug("Enabling manual mode for device %s", self._device_id)
            await self.ws.send(self._zone_id, self._device_id, updates)
            self._is_on = False
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to disable schedule mode: %s", e)
            self._available = False
            self.async_write_ha_state()