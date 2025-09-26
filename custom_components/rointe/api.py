import logging
import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://api.rointe.com/v3"

class RointeAPI:
    """REST API client for Rointe devices."""

    def __init__(self, session: aiohttp.ClientSession, auth_token: str):
        self._session = session
        self._auth_token = auth_token

    async def _request(self, method: str, path: str, json: dict = None):
        """Perform an authenticated REST request."""
        url = f"{BASE_URL}{path}"
        headers = {
            "Authorization": f"Bearer {self._auth_token}",
            "Content-Type": "application/json",
        }

        _LOGGER.debug("REST %s %s %s", method, url, json)
        async with self._session.request(method, url, headers=headers, json=json) as resp:
            text = await resp.text()
            _LOGGER.debug("REST response %s: %s", resp.status, text)
            resp.raise_for_status()
            if "application/json" in resp.headers.get("Content-Type", ""):
                return await resp.json()
            return text

    async def set_temperature(self, device_id: str, temperature: float):
        """Set target temperature for device."""
        body = {"consign": temperature}
        return await self._request("PATCH", f"/devices/{device_id}", body)

    async def set_hvac_mode(self, device_id: str, hvac_mode: str):
        """Set HVAC mode via REST."""
        if hvac_mode == "heat":
            body = {"status": "comfort", "power": 2}
        elif hvac_mode == "off":
            body = {"status": "eco", "power": 1}
        else:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")
        return await self._request("PATCH", f"/devices/{device_id}", body)

    async def set_preset_mode(self, device_id: str, preset_mode: str):
        """Set preset mode via REST."""
        if preset_mode == "comfort":
            body = {"status": "comfort", "power": 2}
        elif preset_mode == "eco":
            body = {"status": "eco", "power": 1}
        else:
            raise ValueError(f"Unsupported preset mode: {preset_mode}")
        return await self._request("PATCH", f"/devices/{device_id}", body)