#!/usr/bin/env python3
"""
Debug script to test device discovery
"""
import asyncio
import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from rointe.auth import RointeAuth

async def test_device_discovery():
    """Test device discovery with current credentials"""
    
    # You'll need to update these with your actual credentials
    email = "your_email@example.com"
    password = "your_password"
    
    print(f"Testing device discovery for {email}")
    
    try:
        # Initialize auth
        auth = RointeAuth(email, password)
        
        # Test REST API login
        print("1. Testing REST API login...")
        await auth.async_login_rest()
        print("✅ REST API login successful")
        
        # Test getting installations
        print("2. Testing installations API...")
        from rointe.api import RointeAPI
        api = RointeAPI(auth)
        
        installations = await api._get("/installations")
        print(f"✅ Found {len(installations)} installations")
        
        for i, inst in enumerate(installations):
            print(f"   Installation {i}: {inst}")
            zones = inst.get("zones", [])
            print(f"     Zones: {zones}")
            
            for zone_id in zones:
                print(f"   Testing zone {zone_id}...")
                zone = await api._get(f"/zones/{zone_id}")
                print(f"     Zone info: {zone}")
                devices = zone.get("devices", [])
                print(f"     Devices in zone: {len(devices)}")
                for device in devices:
                    print(f"       Device: {device}")
        
        # Test full device discovery
        print("3. Testing full device discovery...")
        devices = await api.list_devices()
        print(f"✅ Discovered {len(devices)} devices")
        
        for device in devices:
            print(f"   Device: {device}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Rointe Device Discovery Debug Script")
    print("=" * 50)
    print("Please update the email and password in this script first!")
    print("=" * 50)
    
    # Uncomment the line below after updating credentials
    # asyncio.run(test_device_discovery())
