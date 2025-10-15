"""
Rointe Integration Entry Point
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
    hass.data.setdefault(DOMAIN, {})

    email = entry.data.get("email")
    password = entry.data.get("password")

    if not email or not password:
        _LOGGER.error("Missing email or password in config entry: %s", entry.data)
        raise ConfigEntryNotReady("Missing email or password in configuration")

    _LOGGER.debug(
        "Setting up Rointe integration for entry %s with email: %s",
        entry.entry_id,
        email,
    )

    auth = RointeAuth(email, password)

    # REST login
    try:
        await auth.async_login_rest()
        _LOGGER.info("REST API authentication successful")
    except RointeRestAuthError as e:
        _LOGGER.error("REST API authentication failed: %s", e)
        raise ConfigEntryNotReady(f"REST API authentication failed: {e}")

    # Firebase login
    try:
        await auth.async_login_firebase()
        _LOGGER.info("Firebase authentication successful")
    except RointeFirebaseAuthError as e:
        _LOGGER.warning("Firebase authentication failed: %s", e)
        _LOGGER.warning("WebSocket functionality may be limited")

    # Get user ID directly from auth
    user_id = getattr(auth, "_user_id", None)
    if not user_id:
        _LOGGER.warning("User ID not found, WebSocket will not be available")
        ws = None
    else:
        ws = RointeWebSocket(hass, auth, user_id=user_id)
        try:
            await ws.connect()
            _LOGGER.info("WebSocket connection established for user %s", user_id)
        except Exception as e:
            _LOGGER.error("Failed to establish WebSocket: %s", e)
            ws = None

    # Initialize API
    api = RointeAPI(auth)
    try:
        # Discover devices
        devices = await api.list_devices()
        _LOGGER.info(f"Discovered {len(devices)} devices")
    except (RointeAPIError, RointeNetworkError) as e:
        _LOGGER.error("Device discovery failed: %s", e)
        devices = []

    # Store devices in hass data
    hass.data[DOMAIN][entry.entry_id] = {
        "auth": auth,
        "api": api,
        "devices": devices,
        "ws": ws,
    }

    # Now reconnect WebSocket so it can subscribe to the discovered devices
    _LOGGER.info("Reconnecting WebSocket with discovered devices")
    await ws.disconnect()
    await ws.connect()

    # Forward setups to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Rointe integration setup completed successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, {})

        for key in ["ws", "auth", "api"]:
            obj = data.get(key)
            if obj:
                try:
                    await getattr(obj, "disconnect", getattr(obj, "close", lambda: None))()
                    _LOGGER.debug("%s resource closed", key)
                except Exception as e:
                    _LOGGER.error("Error closing %s: %s", key, e)

        _LOGGER.info("Rointe integration unloaded successfully")
    return unload_ok
