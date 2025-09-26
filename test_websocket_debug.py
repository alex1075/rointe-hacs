#!/usr/bin/env python3
"""Debug WebSocket connection and temperature control."""

import asyncio
import aiohttp
import json
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

async def test_websocket_connection():
    """Test if we can connect to the Rointe WebSocket."""
    
    # This is a simplified test - in reality we'd need proper auth
    websocket_url = "wss://rointe-nexa.firebaseio.com/.ws?v=5&ns=rointe-nexa"
    
    try:
        async with aiohttp.ClientSession() as session:
            _LOGGER.info("Attempting to connect to WebSocket...")
            async with session.ws_connect(websocket_url) as ws:
                _LOGGER.info("✅ WebSocket connected successfully!")
                
                # Send a test message
                test_message = {
                    "t": "d",
                    "d": {
                        "a": "m",
                        "b": {"p": "/test", "d": {"test": "value"}},
                    },
                }
                
                await ws.send_str(json.dumps(test_message))
                _LOGGER.info("✅ Test message sent successfully!")
                
                # Listen for a few messages
                for i in range(3):
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                        _LOGGER.info(f"✅ Received message {i+1}: {msg.data}")
                    except asyncio.TimeoutError:
                        _LOGGER.info(f"No message received within 5 seconds (attempt {i+1})")
                        
    except Exception as e:
        _LOGGER.error(f"❌ WebSocket connection failed: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print("🧪 Testing WebSocket Connection\n")
    
    success = asyncio.run(test_websocket_connection())
    
    if success:
        print("\n🎉 WebSocket test successful!")
    else:
        print("\n💥 WebSocket test failed!")
