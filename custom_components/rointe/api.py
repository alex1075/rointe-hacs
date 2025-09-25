import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://rointenexa.com/api"

class RointeAPI:
    def __init__(self, auth):
        self.auth = auth

    async def _get(self, path):
        token = await self.auth.async_refresh()
        headers = {"token": token}
        url = f"{API_BASE}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception(f"GET {path} failed {resp.status}")
                return await resp.json()

    async def list_devices(self):
        devices = []
        installations = await self._get("/installations")
        for inst in installations:
            for zone_id in inst.get("zones", []):
                zone = await self._get(f"/zones/{zone_id}")
                zone_name = zone.get("name", "Zone")
                for dev in zone.get("devices", []):
                    devices.append(
                        {"id": dev["id"], "name": dev.get("name", dev["id"]), "zone": zone_name}
                    )
        _LOGGER.debug("Discovered devices: %s", devices)
        return devices