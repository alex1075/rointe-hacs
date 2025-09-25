import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, PLATFORMS
from .auth import RointeAuth, RointeAuthenticationError
from .ws import RointeWebSocket
from .api import RointeAPI, RointeAPIError, RointeNetworkError

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Rointe component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Rointe from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    try:
        # Get refresh_token from entry data
        refresh_token = entry.data.get("refresh_token")
        if not refresh_token:
            _LOGGER.error("Missing or empty refresh_token in config entry data: %s", entry.data)
            raise ConfigEntryNotReady("Missing refresh_token in configuration")
        
        _LOGGER.debug("Setting up Rointe integration for entry %s", entry.entry_id)
        
        # Initialize authentication
        auth = RointeAuth(hass, refresh_token)
        
        # Test authentication
        try:
            await auth.async_refresh()
            _LOGGER.info("Authentication successful")
        except RointeAuthenticationError as e:
            _LOGGER.error("Authentication failed: %s", e)
            raise ConfigEntryNotReady(f"Authentication failed: {e}")
        
        # Initialize WebSocket connection
        ws = RointeWebSocket(hass, auth)
        try:
            await ws.connect()
            _LOGGER.info("WebSocket connection established")
        except Exception as e:
            _LOGGER.error("Failed to establish WebSocket connection: %s", e)
            raise ConfigEntryNotReady(f"WebSocket connection failed: {e}")
        
        # Initialize API and discover devices
        api = RointeAPI(auth)
        try:
            devices = await api.list_devices()
            if not devices:
                _LOGGER.warning("No devices discovered")
            else:
                _LOGGER.info("Discovered %d devices", len(devices))
        except (RointeAPIError, RointeNetworkError) as e:
            _LOGGER.error("Device discovery failed: %s", e)
            # Don't fail setup completely - allow partial functionality
            devices = []
        except Exception as e:
            _LOGGER.error("Unexpected error during device discovery: %s", e)
            devices = []
        
        # Store data
        hass.data[DOMAIN][entry.entry_id] = {
            "auth": auth, 
            "ws": ws, 
            "api": api,
            "devices": devices
        }
        
        # Set up platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        _LOGGER.info("Rointe integration setup completed successfully")
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