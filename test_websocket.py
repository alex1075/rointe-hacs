#!/usr/bin/env python3
"""
Quick WebSocket test to debug Rointe Firebase connection and subscription.
This tests the WebSocket connection and subscription without needing HA.
"""

import asyncio
import aiohttp
import json
import sys

# Your credentials (update these)
EMAIL = "subsetc@googlemail.com"
PASSWORD = "your_password_here"  # Update this

# Firebase API key (from the integration)
FIREBASE_API_KEY = "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY"

# Firebase URLs
FIREBASE_URL = "wss://s-gke-euw1-nssi3-8.europe-west1.firebasedatabase.app/.ws?v=5&ns=rointe-v3-prod-default-rtdb"
SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"

async def test_websocket():
    """Test WebSocket connection and subscription."""
    
    print("🔐 Step 1: Getting Firebase token...")
    
    # Get Firebase token
    async with aiohttp.ClientSession() as session:
        # First get user ID from REST API
        rest_data = {
            "email": EMAIL,
            "password": PASSWORD
        }
        
        async with session.post("https://rointenexa.com/api/user/login", json=rest_data) as resp:
            if resp.status != 200:
                print(f"❌ REST API failed: {resp.status}")
                return
            rest_result = await resp.json()
            user_id = rest_result["data"]["user"]["id"]
            print(f"✅ REST API success, user_id: {user_id}")
        
        # Now get Firebase token
        firebase_data = {
            "email": f"{user_id}@rointe.com",
            "password": user_id,
            "returnSecureToken": True
        }
        
        async with session.post(SIGNIN_URL, json=firebase_data) as resp:
            if resp.status != 200:
                print(f"❌ Firebase auth failed: {resp.status}")
                return
            firebase_result = await resp.json()
            id_token = firebase_result["idToken"]
            print(f"✅ Firebase auth success")
    
    print("\n🔌 Step 2: Connecting to WebSocket...")
    
    # Connect to WebSocket
    url = f"{FIREBASE_URL}&auth={id_token}"
    print(f"WebSocket URL: {url[:100]}...")
    
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url) as ws:
            print("✅ WebSocket connected!")
            
            print("\n📡 Step 3: Sending subscription message...")
            
            # Send subscription message
            subscription_msg = {
                "t": "d",
                "d": {
                    "r": 1,
                    "a": "q",
                    "b": {
                        "p": "devices",
                        "q": {
                            "orderBy": "$key"
                        }
                    }
                }
            }
            
            await ws.send_str(json.dumps(subscription_msg))
            print("✅ Subscription message sent!")
            
            print("\n👂 Step 4: Listening for messages (10 seconds)...")
            
            # Listen for messages
            message_count = 0
            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        message_count += 1
                        data = json.loads(msg.data)
                        print(f"📨 Message {message_count}: {data}")
                        
                        # Check if it's a device update
                        if "d" in data and isinstance(data["d"], dict):
                            payload = data["d"]
                            if "b" in payload and "p" in payload["b"]:
                                path = payload["b"]["p"]
                                if path.startswith("devices/") and "/data" in path:
                                    device_id = path.split("/")[1]
                                    state = payload["b"].get("d", {})
                                    print(f"🔥 Device update for {device_id}: {state}")
                                    
                                    # Check for temperature data
                                    if "temp" in state:
                                        print(f"🌡️ Current temperature: {state['temp']}")
                                    if "um_max_temp" in state:
                                        print(f"🎯 Target temperature: {state['um_max_temp']}")
                                    if "status" in state:
                                        print(f"🔥 Status: {state['status']}")
                        
                        # Stop after 10 messages or 10 seconds
                        if message_count >= 10:
                            break
                            
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for messages")
            
            print(f"\n📊 Summary: Received {message_count} messages")
            
            if message_count == 0:
                print("❌ No messages received - WebSocket subscription may not be working")
            else:
                print("✅ WebSocket is receiving messages!")

if __name__ == "__main__":
    print("🚀 Rointe WebSocket Test")
    print("=" * 50)
    
    if PASSWORD == "your_password_here":
        print("❌ Please update the PASSWORD variable in this script")
        sys.exit(1)
    
    asyncio.run(test_websocket())
