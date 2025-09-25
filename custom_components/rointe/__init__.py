from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, PLATFORMS
from .auth import RointeAuth
from .ws import RointeWebSocket
from .api import RointeAPI

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    refresh_token = entry.data["refresh_token"]

    auth = RointeAuth(hass, refresh_token)
    ws = RointeWebSocket(hass, auth)
    await ws.connect()

    api = RointeAPI(auth)
    devices = await api.list_devices()

    hass.data[DOMAIN][entry.entry_id] = {"auth": auth, "ws": ws, "devices": devices}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok