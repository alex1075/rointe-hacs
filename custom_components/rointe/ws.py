"""
Rointe WebSocket Module

Handles WebSocket connection using Firebase authentication.
Uses Firebase ID token for WebSocket authentication.
"""

import aiohttp
import asyncio
import logging
import json
import random
from datetime import datetime
from homeassistant.helpers.dispatcher import async_dispatcher_send

_LOGGER = logging.getLogger(__name__)

FIREBASE_URL = "wss://s-gke-euw1-nssi3-8.europe-west1.firebasedatabase.app/.ws?v=5&ns=rointe-v3-prod-default-rtdb"

SIGNAL_UPDATE = "rointe_device_update"

class RointeWebSocket:
    def __init__(self, hass, auth):
        """Initialize WebSocket client with dual authentication handler"""
        self.hass = hass
        self.auth = auth
        self.ws = None
        self.session = None
        self.running = False
        self.reconnect_task = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_reconnect_delay = 1  # Start with 1 second
        self.max_reconnect_delay = 60  # Max 60 seconds between attempts
        self.jitter_range = 0.1  # Add 10% random jitter
        _LOGGER.debug("Initialized RointeWebSocket with dual authentication")

    async def connect(self):
        """Initial connection to WebSocket."""
        self.running = True
        await self._connect()

    async def _connect(self):
        """Internal method to establish WebSocket connection with Firebase authentication."""
        try:
            # Get valid Firebase ID token from auth handler
            id_token = await self.auth.async_firebase_token()
            url = f"{FIREBASE_URL}&auth={id_token}"
            
            # Create new session if needed
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession()
            
            # Connect to WebSocket
            self.ws = await self.session.ws_connect(url)
            self.reconnect_attempts = 0  # Reset counter on successful connection
            
            _LOGGER.info("Connected to Rointe Firebase WebSocket")
            _LOGGER.debug("WebSocket URL: %s", url)
            
            # Start listening for messages
            asyncio.create_task(self._listen())
            
        except Exception as e:
            _LOGGER.error("Failed to connect to Rointe WebSocket: %s", e)
            await self._schedule_reconnect()

    async def _listen(self):
        """Listen for WebSocket messages."""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error: %s", msg)
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    _LOGGER.warning("WebSocket connection closed by server")
                    break
        except asyncio.CancelledError:
            _LOGGER.debug("WebSocket listen task cancelled")
            raise
        except Exception as e:
            _LOGGER.error("Error in WebSocket listener: %s", e)
        finally:
            await self._handle_disconnection()

    async def _handle_message(self, data):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(data)
            _LOGGER.info("🔥 WebSocket message received: %s", data)
            if "d" in data and isinstance(data["d"], dict):
                payload = data["d"]
                if "b" in payload and "p" in payload["b"]:
                    path = payload["b"]["p"]
                    _LOGGER.info("🔥 WebSocket path: %s", path)
                    if path.startswith("devices/") and "/data" in path:
                        device_id = path.split("/")[1]
                        state = payload["b"].get("d", {})
                        _LOGGER.info("🔥 Sending update to device %s: %s", device_id, state)
                        async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE}_{device_id}", state)
                        _LOGGER.debug("Received update for device %s: %s", device_id, state)
        except json.JSONDecodeError as e:
            _LOGGER.warning("Failed to parse WebSocket message: %s", e)
        except Exception as e:
            _LOGGER.error("Error handling WebSocket message: %s", e)

    async def _handle_disconnection(self):
        """Handle WebSocket disconnection."""
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        if self.running:
            _LOGGER.info("WebSocket disconnected, attempting to reconnect...")
            await self._schedule_reconnect()

    async def _schedule_reconnect(self):
        """Schedule a reconnection attempt with exponential backoff."""
        if not self.running or self.reconnect_attempts >= self.max_reconnect_attempts:
            if self.reconnect_attempts >= self.max_reconnect_attempts:
                _LOGGER.error("Max reconnection attempts reached, giving up")
                self.running = False
            return

        self.reconnect_attempts += 1
        
        # Calculate delay with exponential backoff and jitter
        delay = min(
            self.base_reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
            self.max_reconnect_delay
        )
        
        # Add random jitter to prevent thundering herd
        jitter = random.uniform(-self.jitter_range, self.jitter_range) * delay
        delay = max(0, delay + jitter)
        
        _LOGGER.info("Scheduling reconnection attempt %d/%d in %.1f seconds", 
                    self.reconnect_attempts, self.max_reconnect_attempts, delay)
        
        # Cancel any existing reconnect task
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
        
        self.reconnect_task = asyncio.create_task(self._reconnect_after_delay(delay))

    async def _reconnect_after_delay(self, delay):
        """Reconnect after a delay."""
        try:
            await asyncio.sleep(delay)
            if self.running:
                await self._connect()
        except asyncio.CancelledError:
            _LOGGER.debug("Reconnect task cancelled")
        except Exception as e:
            _LOGGER.error("Error during reconnection: %s", e)
            await self._schedule_reconnect()

    async def send(self, device_id: str, updates: dict):
        """Send updates to a device via WebSocket."""
        if not self.ws or self.ws.closed:
            _LOGGER.warning("WebSocket not connected, cannot send update for device %s", device_id)
            raise Exception("WebSocket not connected")
        
        try:
            # Generate a request ID (incrementing counter)
            request_id = getattr(self, '_request_counter', 0) + 1
            self._request_counter = request_id
            
            frame = {
                "t": "d",
                "d": {
                    "r": request_id,
                    "a": "m",
                    "b": {"p": f"/devices/{device_id}/data", "d": updates},
                },
            }
            message = json.dumps(frame)
            await self.ws.send_str(message)
            _LOGGER.info("🔥 SENT WebSocket message: %s", message)
            _LOGGER.debug("Sent update to device %s: %s", device_id, updates)
        except Exception as e:
            _LOGGER.error("Failed to send update to device %s: %s", device_id, e)
            raise

    async def disconnect(self):
        """Disconnect from WebSocket and cleanup."""
        _LOGGER.info("Disconnecting from Rointe WebSocket")
        self.running = False
        
        # Cancel reconnect task
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
        
        # Close WebSocket
        if self.ws and not self.ws.closed:
            await self.ws.close()
            self.ws = None
        
        # Close session
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None