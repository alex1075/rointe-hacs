"""
Rointe Integration Entry Point

Handles setup and teardown of the dual authentication system.
"""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, PLATFORMS
from .auth import RointeAuth, RointeRestAuthError, RointeFirebaseAuthError
from .ws import RointeWebSocket
from .api import RointeAPI, RointeAPIError, RointeNetworkError

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Rointe component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Rointe from a config entry using dual authentication."""
    _LOGGER.info("🚀 STARTING Rointe integration setup for entry: %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    
    try:
        # Get email and password from entry data
        email = entry.data.get("email")
        password = entry.data.get("password")
        
        if not email or not password:
            _LOGGER.error("Missing email or password in config entry data: %s", entry.data)
            raise ConfigEntryNotReady("Missing email or password in configuration")
        
        _LOGGER.debug("Setting up Rointe integration for entry %s with email: %s", entry.entry_id, email)
        
        # Initialize dual authentication system
        auth = RointeAuth(email, password)
        
        # Test REST API authentication first
        try:
            _LOGGER.debug("Testing REST API authentication")
            await auth.async_login_rest()
            _LOGGER.info("REST API authentication successful")
        except RointeRestAuthError as e:
            _LOGGER.error("REST API authentication failed: %s", e)
            raise ConfigEntryNotReady(f"REST API authentication failed: {e}")
        
        # Test Firebase authentication
        try:
            _LOGGER.debug("Testing Firebase authentication")
            await auth.async_login_firebase()
            _LOGGER.info("Firebase authentication successful")
        except RointeFirebaseAuthError as e:
            _LOGGER.warning("Firebase authentication failed: %s", e)
            _LOGGER.warning("WebSocket functionality may be limited")
            # Don't fail setup completely - REST API might still work
        
        # Initialize WebSocket connection (if Firebase auth succeeded)
        ws = None
        try:
            if auth.is_firebase_token_valid():
                ws = RointeWebSocket(hass, auth)
                await ws.connect()
                _LOGGER.info("WebSocket connection established")
            else:
                _LOGGER.warning("Firebase token not available, skipping WebSocket connection")
        except Exception as e:
            _LOGGER.error("Failed to establish WebSocket connection: %s", e)
            _LOGGER.warning("Continuing without WebSocket - REST API functionality available")
            ws = None
        
        # Initialize API and discover devices
        api = RointeAPI(auth)
        try:
            _LOGGER.debug("Starting device discovery")
            devices = await api.list_devices()
            if not devices:
                _LOGGER.warning("No devices discovered")
            else:
                _LOGGER.info("Discovered %d devices", len(devices))
                for device in devices:
                    _LOGGER.debug("Device: %s (%s) in zone %s", 
                                device.get("id"), device.get("name"), device.get("zone"))
        except (RointeAPIError, RointeNetworkError) as e:
            _LOGGER.error("Device discovery failed: %s", e)
            # Don't fail setup completely - allow partial functionality
            devices = []
        except Exception as e:
            _LOGGER.error("Unexpected error during device discovery: %s", e)
            devices = []
        
        # Create device-to-zone mapping for WebSocket
        device_zone_mapping = {}
        for device in devices:
            device_id = device.get("id")
            zone_id = device.get("zone_id")
            if zone_id:
                device_zone_mapping[device_id] = zone_id
            else:
                _LOGGER.warning("No zone_id found for device %s", device_id)
        
        # Store device-zone mapping in WebSocket
        if ws:
            ws._device_zone_mapping = device_zone_mapping
        
        # Store data
        hass.data[DOMAIN][entry.entry_id] = {
            "auth": auth, 
            "ws": ws, 
            "api": api,
            "devices": devices,
            "email": email
        }
        
        # Set up platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        _LOGGER.info("Rointe integration setup completed successfully with dual authentication")
        return True
        
    except Exception as e:
        _LOGGER.error("Error setting up Rointe integration: %s", e)
        raise ConfigEntryNotReady(f"Setup failed: {e}")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading Rointe integration for entry %s", entry.entry_id)
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, {})
        
        # Clean up resources
        try:
            if "ws" in data and data["ws"]:
                await data["ws"].disconnect()
                _LOGGER.debug("WebSocket disconnected")
        except Exception as e:
            _LOGGER.error("Error disconnecting WebSocket: %s", e)
        
        try:
            if "auth" in data and data["auth"]:
                await data["auth"].close()
                _LOGGER.debug("Auth session closed")
        except Exception as e:
            _LOGGER.error("Error closing auth session: %s", e)
        
        try:
            if "api" in data and data["api"]:
                await data["api"].close()
                _LOGGER.debug("API session closed")
        except Exception as e:
            _LOGGER.error("Error closing API session: %s", e)
        
        _LOGGER.info("Rointe integration unloaded successfully")
    
    return unload_ok