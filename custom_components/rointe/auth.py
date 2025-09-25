import aiohttp
import logging
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

FIREBASE_API_KEY = "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY"
REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"

class RointeAuth:
    def __init__(self, hass, refresh_token: str):
        self.hass = hass
        self.refresh_token = refresh_token
        self.id_token = None
        self.expiry = datetime.utcnow()

    async def async_refresh(self):
        if self.id_token and datetime.utcnow() < self.expiry:
            return self.id_token

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(REFRESH_URL, data=payload) as resp:
                if resp.status != 200:
                    raise Exception(f"Token refresh failed {resp.status}")
                data = await resp.json()
                self.id_token = data["id_token"]
                self.refresh_token = data["refresh_token"]
                self.expiry = datetime.utcnow() + timedelta(seconds=int(data["expires_in"]) - 60)
                _LOGGER.debug("Refreshed idToken, expires %s", self.expiry)
                return self.id_token