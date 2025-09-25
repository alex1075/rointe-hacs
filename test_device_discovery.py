#!/usr/bin/env python3
"""
Test device discovery with fixed API parsing
"""
import asyncio
import aiohttp
import json

async def test_device_discovery():
    """Test the fixed device discovery logic"""
    
    email = "subsetc@googlemail.com"
    password = "RTMsd.ZvWvxLUL4J"
    
    print("Testing fixed device discovery logic...")
    
    async with aiohttp.ClientSession() as session:
        # Login
        login_data = {"email": email, "password": password}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://rointenexa.com",
            "Referer": "https://rointenexa.com/"
        }
        
        async with session.post("https://rointenexa.com/api/user/login", 
                              json=login_data, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                token = data["data"]["token"]
                print("✅ Login successful")
                
                # Get installations with fixed parsing
                api_headers = {"token": token}
                async with session.get("https://rointenexa.com/api/installations", 
                                     headers=api_headers) as resp:
                    if resp.status == 200:
                        installations_response = await resp.json()
                        
                        # Extract installations from nested 'data' key (FIXED!)
                        if isinstance(installations_response, dict) and "data" in installations_response:
                            installations = installations_response["data"]
                        else:
                            installations = installations_response
                        
                        print(f"✅ Found {len(installations)} installations")
                        
                        devices = []
                        
                        # Process each installation (FIXED LOGIC)
                        for i, inst in enumerate(installations):
                            zones = inst.get("zones", [])
                            print(f"Installation {i}: {inst.get('name', 'Unknown')} - {len(zones)} zones")
                            
                            # Process each zone (zones now contain devices directly)
                            for zone in zones:
                                zone_id = zone.get("id")
                                zone_name = zone.get("name", f"Zone {zone_id}")
                                devices_list = zone.get("devices", [])
                                
                                print(f"  Zone: {zone_name} - {len(devices_list)} devices")
                                
                                # Process each device
                                for device in devices_list:
                                    device_id = device.get("id")
                                    device_name = device.get("name", device_id)
                                    
                                    device_info = {
                                        "id": device_id,
                                        "name": device_name,
                                        "zone": zone_name,
                                        "serialNumber": device.get("serialNumber"),
                                        "mac": device.get("mac"),
                                        "deviceStatus": device.get("deviceStatus"),
                                    }
                                    devices.append(device_info)
                                    print(f"    ✅ Device: {device_name} ({device_id})")
                        
                        print(f"\n🎯 TOTAL DEVICES DISCOVERED: {len(devices)}")
                        for device in devices:
                            print(f"  - {device['name']} in {device['zone']}")
                        
                        return len(devices) > 0
                    else:
                        error_text = await resp.text()
                        print(f"❌ Installations error: {error_text}")
                        return False
            else:
                error_text = await resp.text()
                print(f"❌ Login failed: {error_text}")
                return False

if __name__ == "__main__":
    success = asyncio.run(test_device_discovery())
    if success:
        print("\n✅ Device discovery should now work in Home Assistant!")
    else:
        print("\n❌ Device discovery still has issues")
