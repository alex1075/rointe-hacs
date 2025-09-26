"""Climate platform for Rointe heaters with Comfort/Eco/Ice presets."""

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE

from .api import RointeAPI, RointeDeviceError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Preset modes
PRESET_COMFORT = "comfort"
PRESET_ECO = "eco"
PRESET_ICE = "ice"
PRESET_MODES = [PRESET_COMFORT, PRESET_ECO, PRESET_ICE]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Rointe climate entities from config entry."""
    api: RointeAPI = hass.data[DOMAIN][entry.entry_id]["api"]

    devices = []
    for installation in api.installations:
        for zone in installation["zones"]:
            for device in zone["devices"]:
                devices.append(
                    RointeHeater(api, device, zone["name"])
                )

    if devices:
        async_add_entities(devices, update_before_add=True)
        _LOGGER.info("Successfully set up %s Rointe climate entities", len(devices))


class RointeHeater(ClimateEntity):
    """Representation of a Rointe heater as a HA Climate entity."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = PRESET_MODES

    def __init__(self, api: RointeAPI, device: dict, zone_name: str):
        """Initialize Rointe heater entity."""
        self.api = api
        self.device_id = device["id"]
        self._name = f"{zone_name} - {device['name']}"

        self._attr_unique_id = self.device_id
        self._attr_name = self._name

        # Defaults
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_hvac_action = HVACAction.OFF
        self._attr_preset_mode = PRESET_COMFORT
        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._attr_min_temp = 7
        self._attr_max_temp = 30

        _LOGGER.debug("Created climate entity for device %s: %s", self.device_id, self._name)

    @property
    def name(self):
        return self._name

    async def async_update(self) -> None:
        """Fetch latest state from Rointe API."""
        try:
            data = await self.api.get_device_state(self.device_id)
            if not data:
                return

            self._attr_current_temperature = data.get("temp")
            self._attr_target_temperature = data.get("comfort")

            status = data.get("status", "ice")
            if status == PRESET_COMFORT:
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_hvac_action = HVACAction.HEATING
                self._attr_preset_mode = PRESET_COMFORT
            elif status == PRESET_ECO:
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_hvac_action = HVACAction.HEATING
                self._attr_preset_mode = PRESET_ECO
            elif status == PRESET_ICE:
                self._attr_hvac_mode = HVACMode.OFF
                self._attr_hvac_action = HVACAction.OFF
                self._attr_preset_mode = PRESET_ICE

        except Exception as e:
            _LOGGER.error("Failed to update device %s: %s", self.device_id, e)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature (comfort mode only)."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        try:
            updates = {"comfort": temperature}
            _LOGGER.debug("Setting comfort temperature %s for device %s", temperature, self.device_id)
            await self.api.set_device_state(self.device_id, updates)

            self._attr_target_temperature = temperature
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to set temperature for device %s: %s", self.device_id, e)
            raise RointeDeviceError(f"Failed to set temperature: {e}")

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode (maps to presets)."""
        if hvac_mode == HVACMode.OFF:
            await self.async_set_preset_mode(PRESET_ICE)
        elif hvac_mode == HVACMode.HEAT:
            await self.async_set_preset_mode(PRESET_COMFORT)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode (comfort/eco/ice)."""
        if preset_mode not in PRESET_MODES:
            _LOGGER.error("Invalid preset mode: %s", preset_mode)
            return

        try:
            updates = {"status": preset_mode}
            _LOGGER.debug("Sending preset update for %s: %s", self.device_id, updates)
            await self.api.set_device_state(self.device_id, updates)

            self._attr_preset_mode = preset_mode

            if preset_mode == PRESET_COMFORT:
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_hvac_action = HVACAction.HEATING
            elif preset_mode == PRESET_ECO:
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_hvac_action = HVACAction.HEATING
            elif preset_mode == PRESET_ICE:
                self._attr_hvac_mode = HVACMode.OFF
                self._attr_hvac_action = HVACAction.OFF

            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.error("Error setting preset mode %s for device %s: %s", preset_mode, self.device_id, e)
            raise RointeDeviceError(f"Failed to set preset mode: {e}")