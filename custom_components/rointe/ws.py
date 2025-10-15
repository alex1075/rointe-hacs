import aiohttp
import asyncio
import json
import logging
import random
from datetime import datetime
from homeassistant.helpers.dispatcher import async_dispatcher_send

_LOGGER = logging.getLogger(__name__)

FIREBASE_URL = (
    "wss://s-gke-euw1-nssi3-8.europe-west1.firebasedatabase.app/"
    ".ws?v=5&p=1:382027417649:web:9d854d5f609732ecc56d10&ns=rointe-v3-prod-default-rtdb"
)
REST_API_BASE = "https://rointenexa.com/api"
SIGNAL_UPDATE = "rointe_device_update"


class RointeWebSocket:
    """Firebase WebSocket connection for Rointe devices."""

    def __init__(self, hass, auth, user_id=None):
        self.hass = hass
        self.auth = auth
        self._user_id = user_id
        self.session = None
        self.ws = None
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_reconnect_delay = 1
        self.max_reconnect_delay = 60
        self.jitter_range = 0.1
        self.reconnect_task = None
        self._rid = 100  # request counter
        self._keepalive_task = None
        self._pending_requests = {}  # Track pending requests

    def _next_rid(self):
        """Get next request ID."""
        self._rid += 1
        return self._rid

    # -------------------- CONNECTION --------------------

    async def connect(self):
        """Public entry point."""
        self.running = True
        await self._connect()

    async def _connect(self):
        try:
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession()

            self.ws = await self.session.ws_connect(
                FIREBASE_URL, origin="https://rointe-v3-prod.firebaseapp.com"
            )
            _LOGGER.info("Connected to Firebase WebSocket backend")
            self.reconnect_attempts = 0
            # DON'T reset _rid here if reconnecting!
            if self._rid == 100:  # Only reset on first connection
                self._rid = 0

            await self._handshake_and_auth()
            await self._subscribe_to_devices()

            # Start keep-alive and message listener
            self._keepalive_task = asyncio.create_task(self._send_keepalive())
            asyncio.create_task(self._listen())
        except Exception as e:
            _LOGGER.error("WebSocket connection failed: %s", e)
            await self._schedule_reconnect()

    async def _handshake_and_auth(self):
        """Perform Firebase wire protocol handshake and authentication."""
        try:
            id_token = await self.auth.async_firebase_token()
            if not self._user_id:
                self._user_id = self.auth.get_user_id()

            # Handshake - always r:1
            handshake = {"t": "d", "d": {"r": self._next_rid(), "a": "s", "b": {"c": {"sdk.js.10-14-1": 1}}}}
            await self.ws.send_str(json.dumps(handshake))
            _LOGGER.debug("Sent Firebase handshake (r:%d)", handshake["d"]["r"])

            # Auth - always r:2
            auth_msg = {"t": "d", "d": {"r": self._next_rid(), "a": "auth", "b": {"cred": id_token}}}
            await self.ws.send_str(json.dumps(auth_msg))
            _LOGGER.debug("Sent Firebase auth (r:%d)", auth_msg["d"]["r"])
            
        except Exception as e:
            _LOGGER.error("Failed during handshake/auth: %s", e)

    async def _send_and_wait(self, msg, timeout=5.0):
        """Send a message and wait for response."""
        request_id = msg["d"]["r"]
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        await self.ws.send_str(json.dumps(msg))
        
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            _LOGGER.warning("Request %d timed out", request_id)
            return None

    async def _subscribe_to_devices(self):
        """Subscribe to Firebase device paths with GET requests first."""
        try:
            rointe_data = self.hass.data.get("rointe", {})
            entry_data = None
            
            for entry_id, data in rointe_data.items():
                if isinstance(data, dict) and "devices" in data:
                    entry_data = data
                    break
            
            if not entry_data or not entry_data.get("devices"):
                _LOGGER.warning("No devices found for WebSocket subscription")
                return
            
            devices = entry_data["devices"]
            zone_ids = set(d.get("zone_id") for d in devices if d.get("zone_id"))
            
            # GET zones and wait for responses
            for zone_id in zone_ids:
                msg = {
                    "t": "d",
                    "d": {"r": self._next_rid(), "a": "g", "b": {"p": f"/zones/{zone_id}/data", "q": {}}},
                }
                response = await self._send_and_wait(msg)
                if response:
                    _LOGGER.debug("Got zone data for %s", zone_id)
            
            # GET devices and wait for responses
            for device in devices:
                serial = device.get("serialNumber")
                if not serial:
                    continue
                
                msg = {
                    "t": "d",
                    "d": {"r": self._next_rid(), "a": "g", "b": {"p": f"/devices/{serial}", "q": {}}},
                }
                response = await self._send_and_wait(msg)
                if response:
                    _LOGGER.debug("Got device data for %s", serial)
            
            # Now subscribe
            for zone_id in zone_ids:
                msg = {
                    "t": "d",
                    "d": {"r": self._next_rid(), "a": "q", "b": {"p": f"/zones/{zone_id}/data", "h": ""}},
                }
                await self.ws.send_str(json.dumps(msg))
                _LOGGER.debug("Subscribed to zone: %s", zone_id)
        
            for device in devices:
                serial = device.get("serialNumber")
                if not serial:
                    continue
                
                msg = {
                    "t": "d",
                    "d": {"r": self._next_rid(), "a": "q", "b": {"p": f"/devices/{serial}", "h": ""}},
                }
                await self.ws.send_str(json.dumps(msg))
                _LOGGER.debug("Subscribed to device: %s", serial)
        
            _LOGGER.info("Subscribed to %d zones and %d devices", len(zone_ids), len(devices))
            
        except Exception as e:
            _LOGGER.error("Subscription error: %s", e)

    # -------------------- MESSAGE LOOP --------------------

    async def _send_keepalive(self):
        """Send periodic keep-alive messages to Firebase."""
        try:
            while self.running and self.ws and not self.ws.closed:
                await asyncio.sleep(25)  # Send every 25 seconds (like web app)
                if self.ws and not self.ws.closed:
                    await self.ws.send_str("0")
                    _LOGGER.debug("Sent keep-alive")
        except Exception as e:
            _LOGGER.error("Keep-alive error: %s", e)

    async def _listen(self):
        """Main WebSocket message loop."""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # Ignore keep-alive responses from server
                    if msg.data.strip() == "0":
                        continue
                    await self._handle_message(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    _LOGGER.warning("WebSocket closed or error: %s", msg)
                    break
        except Exception as e:
            _LOGGER.error("Listener crashed: %s", e)
        finally:
            await self._handle_disconnection()

    async def _handle_message(self, data):
        """Parse messages pushed from Firebase."""
        _LOGGER.debug("Raw Firebase message: %s", data)
        try:
            payload = json.loads(data)
            if payload.get("t") != "d":
                return
            body = payload.get("d", {})
            
            # Handle request responses
            if "r" in body and body["r"] in self._pending_requests:
                request_id = body["r"]
                future = self._pending_requests.pop(request_id)
                if not future.done():
                    future.set_result(body)
                return
            
            if "b" not in body:
                return
            b = body["b"]
            
            # Handle data updates
            if "p" in b and "d" in b and b.get("a") in ("d", "m"):
                path = b["p"]
                updates = b["d"]
                
                # Zone updates - dispatch to all devices in that zone
                if path.startswith("zones/") and "/data" in path:
                    zone_id = path.split("/")[1]
                    _LOGGER.debug("Zone update for %s: %s", zone_id, updates)
                    
                    # Find all devices in this zone and update them
                    rointe_data = self.hass.data.get("rointe", {})
                    for entry_id, entry_data in rointe_data.items():
                        if isinstance(entry_data, dict) and "devices" in entry_data:
                            for device in entry_data["devices"]:
                                if device.get("zone_id") == zone_id:
                                    device_id = device.get("id")  # Still use UUID for internal dispatch
                                    if device_id:
                                        async_dispatcher_send(
                                            self.hass, 
                                            f"{SIGNAL_UPDATE}_{device_id}", 
                                            updates
                                        )
            
                # Device updates - Firebase uses serial number in path
                elif path.startswith("devices/"):
                    serial = path.split("/")[1]  # Extract serial from path
                    
                    # Map serial number to UUID for internal dispatch
                    rointe_data = self.hass.data.get("rointe", {})
                    device_uuid = None
                    for entry_id, entry_data in rointe_data.items():
                        if isinstance(entry_data, dict) and "devices" in entry_data:
                            for device in entry_data["devices"]:
                                if device.get("serialNumber") == serial:
                                    device_uuid = device.get("id")
                                    break
                        if device_uuid:
                            break
                    
                    if not device_uuid:
                        _LOGGER.warning("No device found for serial %s", serial)
                        return
                    
                    # Handle full device snapshot (a: "d")
                    if "data" in updates and isinstance(updates["data"], dict):
                        device_data = updates["data"]
                        async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE}_{device_uuid}", device_data)
                        _LOGGER.debug("Full device update for %s (serial: %s)", device_uuid, serial)
                    
                    # Handle incremental updates (a: "m") to /data path
                    elif "/data" in path:
                        async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE}_{device_uuid}", updates)
                        _LOGGER.debug("Incremental update for %s (serial: %s): %s", device_uuid, serial, updates)
                
        except Exception as e:
            _LOGGER.error("Failed to process message: %s", e)

    # -------------------- COMMAND SEND --------------------

    async def send(self, zone_id: str, device_id: str, updates: dict):
        """Send updates via the persistent WebSocket connection."""
        if not self.ws or self.ws.closed:
            _LOGGER.error("WebSocket not connected, cannot send update")
            return
        
        try:
            # IMPORTANT: Don't merge with device_state from hass.data!
            # That contains REST API metadata, not Firebase device fields
            
            # Get serial number only
            device_serial = None
            rointe_data = self.hass.data.get("rointe", {})
            for entry_id, entry_data in rointe_data.items():
                if isinstance(entry_data, dict) and "devices" in entry_data:
                    for device in entry_data["devices"]:
                        if device.get("id") == device_id:
                            device_serial = device.get("serialNumber")
                            break
                if device_serial:
                    break
            
            if not device_serial:
                _LOGGER.error("Device %s has no serial number", device_id)
                return
            
            # Add timestamp to updates
            updates["last_sync_datetime_device"] = int(datetime.now().timestamp() * 1000)
            
            # Send ONLY the updates - don't merge with full state!
            device_frame = {
                "t": "d",
                "d": {
                    "r": self._next_rid(),
                    "b": {
                        "p": f"/devices/{device_serial}/data",
                        "d": updates
                    },
                    "a": "m"
                }
            }
            
            json_payload = json.dumps(device_frame)
            _LOGGER.warning("SENDING: r=%d, fields=%d, JSON: %s", 
                           device_frame["d"]["r"], len(updates), json_payload)
            
            await self.ws.send_str(json_payload)
            _LOGGER.info("Sent update (r:%d) to %s", device_frame["d"]["r"], device_id)
        
        except Exception as e:
            _LOGGER.error("Error sending update: %s", e, exc_info=True)

    # -------------------- DISCONNECTION --------------------

    async def _handle_disconnection(self):
        """Handle unexpected disconnection."""
        _LOGGER.warning("WebSocket disconnected")
        
        # Cancel keep-alive task
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            self._keepalive_task = None
        
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        if self.running:
            await self._schedule_reconnect()

    async def disconnect(self):
        """Gracefully disconnect."""
        _LOGGER.info("Disconnecting WebSocket")
        self.running = False
        
        # Cancel keep-alive task
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            self._keepalive_task = None
        
        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self.session and not self.session.closed:
            await self.session.close()

    async def _schedule_reconnect(self):
        """Schedule a reconnection with exponential backoff."""
        if not self.running or self.reconnect_attempts >= self.max_reconnect_attempts:
            _LOGGER.error("Max reconnection attempts reached")
            return

        self.reconnect_attempts += 1
        delay = min(
            self.base_reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
            self.max_reconnect_delay,
        )
        jitter = random.uniform(-self.jitter_range, self.jitter_range) * delay
        delay = max(0, delay + jitter)

        _LOGGER.warning("Reconnecting in %.1fs...", delay)
        await asyncio.sleep(delay)
        await self._connect()

    async def _rest_fallback(self, device_id: str, updates: dict):
        """Fallback to REST API if WebSocket fails."""
        _LOGGER.info("Using REST API fallback for device %s", device_id)
        try:
            # You'll need to import your REST API client
            # This is a placeholder - adjust based on your actual REST implementation
            pass
        except Exception as e:
            _LOGGER.error("REST fallback also failed: %s", e)

