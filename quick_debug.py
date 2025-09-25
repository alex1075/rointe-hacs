#!/usr/bin/env python3
"""
Quick debug script to test Rointe API endpoints
"""
import asyncio
import aiohttp
import json

async def test_rointe_api():
    """Test Rointe API endpoints directly"""
    
    # Update these with your actual credentials
    email = "subsetc@googlemail.com"
    password = "RTMsd.ZvWvxLUL4J"
    
    print("Testing Rointe API endpoints...")
    
    # Step 1: Test login
    print("1. Testing login...")
    async with aiohttp.ClientSession() as session:
        login_data = {
            "email": email,
            "password": password
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://rointenexa.com",
            "Referer": "https://rointenexa.com/"
        }
        
        try:
            async with session.post("https://rointenexa.com/api/user/login", 
                                  json=login_data, headers=headers) as resp:
                print(f"   Login response status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    print("   ✅ Login successful")
                    print(f"   Response keys: {list(data.keys())}")
                    
                    if "data" in data and "token" in data["data"]:
                        token = data["data"]["token"]
                        print(f"   Token: {token[:20]}...")
                        
                        # Step 2: Test installations
                        print("2. Testing installations...")
                        api_headers = {"token": token}
                        
                        async with session.get("https://rointenexa.com/api/installations", 
                                             headers=api_headers) as resp:
                            print(f"   Installations response status: {resp.status}")
                            
                            if resp.status == 200:
                                installations_data = await resp.json()
                                print(f"   ✅ Installations response: {installations_data}")
                                
                                # Check if installations is nested in a 'data' key
                                if isinstance(installations_data, dict) and "data" in installations_data:
                                    installations = installations_data["data"]
                                else:
                                    installations = installations_data
                                
                                print(f"   Found {len(installations)} installations")
                                
                                for i, inst in enumerate(installations):
                                    print(f"   Installation {i}: {inst}")
                                    print(f"   Installation type: {type(inst)}")
                                    
                                    if isinstance(inst, dict):
                                        zones = inst.get("zones", [])
                                        print(f"     Zones: {zones}")
                                    else:
                                        print(f"     Installation is not a dict: {inst}")
                                    
                                    # Test first zone if available
                                    if zones:
                                        zone_id = zones[0]
                                        print(f"   Testing zone {zone_id}...")
                                        
                                        async with session.get(f"https://rointenexa.com/api/zones/{zone_id}", 
                                                             headers=api_headers) as resp:
                                            print(f"     Zone response status: {resp.status}")
                                            
                                            if resp.status == 200:
                                                zone_data = await resp.json()
                                                print(f"     ✅ Zone data: {zone_data}")
                                                devices = zone_data.get("devices", [])
                                                print(f"     Devices in zone: {len(devices)}")
                                                for device in devices:
                                                    print(f"       Device: {device}")
                                            else:
                                                error_text = await resp.text()
                                                print(f"     ❌ Zone error: {error_text}")
                            else:
                                error_text = await resp.text()
                                print(f"   ❌ Installations error: {error_text}")
                    else:
                        print("   ❌ No token in response")
                        print(f"   Full response: {data}")
                else:
                    error_text = await resp.text()
                    print(f"   ❌ Login failed: {error_text}")
                    
        except Exception as e:
            print(f"   ❌ Request failed: {e}")

if __name__ == "__main__":
    print("Rointe API Quick Debug")
    print("=" * 30)
    print("Please update the email and password in this script first!")
    print("=" * 30)
    
    # Run the test
    asyncio.run(test_rointe_api())
