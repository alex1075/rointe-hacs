import aiohttp
import asyncio
import logging
import json
from homeassistant.helpers.dispatcher import async_dispatcher_send

_LOGGER = logging.getLogger(__name__)

FIREBASE_URL = "wss://s-gke-euw1-nssi3-8.europe-west1.firebasedatabase.app/.ws?v=5&ns=rointe-v3-prod-default-rtdb"

SIGNAL_UPDATE = "rointe_device_update"

class RointeWebSocket:
    def __init__(self, hass, auth):
        self.hass = hass
        self.auth = auth
        self.ws = None
        self.running = False

    async def connect(self):
        id_token = await self.auth.async_refresh()
        url = f"{FIREBASE_URL}&auth={id_token}"
        session = aiohttp.ClientSession()
        self.ws = await session.ws_connect(url)
        self.running = True
        _LOGGER.info("Connected to Rointe Firebase WS")
        asyncio.create_task(self._listen())

    async def _listen(self):
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if "d" in data and isinstance(data["d"], dict):
                        payload = data["d"]
                        if "b" in payload and "p" in payload["b"]:
                            path = payload["b"]["p"]
                            if path.startswith("devices/") and "/data" in path:
                                device_id = path.split("/")[1]
                                state = payload["b"].get("d", {})
                                async_dispatcher_send(self.hass, SIGNAL_UPDATE, device_id, state)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("WS error: %s", msg)
                    break
        finally:
            self.running = False
            await self.ws.close()

    async def send(self, device_id: str, updates: dict):
        if not self.ws:
            raise Exception("WS not connected")
        frame = {
            "t": "d",
            "d": {
                "a": "m",
                "b": {"p": f"/devices/{device_id}/data", "d": updates},
            },
        }
        await self.ws.send_str(json.dumps(frame))
        _LOGGER.debug("Sent %s", frame)