"""
Rointe Integration Entry Point
"""

import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, PLATFORMS
from .auth import RointeAuth, RointeRestAuthError, RointeFirebaseAuthError
from .ws import RointeWebSocket
from .api import RointeAPI, RointeAPIError, RointeNetworkError

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Rointe component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rointe from a config entry."""
    try:
        _LOGGER.debug("Setting up Rointe integration for entry %s", entry.entry_id)

        # Initialize REST API authentication
        auth = RointeAuth(
            email=entry.data.get("email"),
            password=entry.data.get("password")
        )

        # Perform REST login
        if not await auth.async_login_rest():
            _LOGGER.error("Failed to authenticate with Rointe REST API")
            return False

        _LOGGER.info("REST API authentication successful")

        # Perform Firebase login
        if not await auth.async_login_firebase():
            _LOGGER.error("Failed to authenticate with Firebase")
            return False

        _LOGGER.info("Firebase authentication successful")

        # Initialize API client
        api = RointeAPI(auth)

        # Discover devices using REST API
        devices = await api.list_devices()  # Changed to list_devices
        _LOGGER.info("Discovered %d devices", len(devices))

        # CRITICAL: Store devices in hass.data BEFORE connecting WebSocket
        hass.data.setdefault("rointe", {})[entry.entry_id] = {
            "api": api,
            "ws": None,  # Will be set after connection
            "devices": devices,
        }

        # NOW connect WebSocket - it will find the devices!
        ws = RointeWebSocket(hass, auth, auth._user_id)
        await ws.connect()
        _LOGGER.info("WebSocket connection established")

        # Update the stored ws reference
        hass.data["rointe"][entry.entry_id]["ws"] = ws

        # Set up platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        _LOGGER.info("Rointe integration setup completed successfully")
        return True

    except Exception as e:
        _LOGGER.error("Error setting up Rointe integration: %s", e)
        import traceback
        _LOGGER.error("Traceback: %s", traceback.format_exc())
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, {})

        # Disconnect WebSocket
        ws = data.get("ws")
        if ws:
            try:
                await ws.disconnect()
                _LOGGER.debug("WebSocket disconnected")
            except Exception as e:
                _LOGGER.error("Error disconnecting WebSocket: %s", e)

        _LOGGER.info("Rointe integration unloaded successfully")

    return unload_ok
