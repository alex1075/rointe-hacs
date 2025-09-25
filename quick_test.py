#!/usr/bin/env python3
"""
Quick test script for Rointe integration.
Run this to verify basic functionality without Home Assistant.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

# Add the integration to path
sys.path.insert(0, str(Path(__file__).parent / "custom_components"))

def test_imports():
    """Test that all modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from rointe import async_setup_entry
        from rointe.auth import RointeAuth, RointeAuthenticationError
        from rointe.api import RointeAPI, RointeAPIError, RointeNetworkError
        from rointe.ws import RointeWebSocket
        from rointe.climate import RointeHeater, HVAC_MODES, PRESET_MODES
        from rointe.config_flow import RointeConfigFlow
        from rointe.const import DOMAIN, PLATFORMS
        print("✅ All imports successful!")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_auth_class():
    """Test RointeAuth class."""
    print("\n🧪 Testing RointeAuth class...")
    
    try:
        from rointe.auth import RointeAuth
        
        # Mock Home Assistant
        mock_hass = MagicMock()
        auth = RointeAuth(mock_hass, "test_refresh_token")
        
        # Test basic properties
        assert auth.refresh_token == "test_refresh_token"
        assert auth.id_token is None
        
        # Test token validation
        assert not auth.is_token_valid()
        
        # Mock valid token
        auth.id_token = "test_token"
        auth.expiry = datetime.utcnow() + timedelta(hours=1)
        assert auth.is_token_valid()
        
        # Test token info
        info = auth.get_token_info()
        assert info["has_token"] is True
        assert info["is_valid"] is True
        
        print("✅ RointeAuth class tests passed!")
        return True
    except Exception as e:
        print(f"❌ RointeAuth test failed: {e}")
        return False

def test_api_class():
    """Test RointeAPI class."""
    print("\n🧪 Testing RointeAPI class...")
    
    try:
        from rointe.api import RointeAPI
        
        # Mock auth
        mock_auth = MagicMock()
        api = RointeAPI(mock_auth)
        
        assert api.auth == mock_auth
        assert api.session is None
        
        print("✅ RointeAPI class tests passed!")
        return True
    except Exception as e:
        print(f"❌ RointeAPI test failed: {e}")
        return False

def test_websocket_class():
    """Test RointeWebSocket class."""
    print("\n🧪 Testing RointeWebSocket class...")
    
    try:
        from rointe.ws import RointeWebSocket
        
        # Mock Home Assistant and auth
        mock_hass = MagicMock()
        mock_auth = MagicMock()
        
        ws = RointeWebSocket(mock_hass, mock_auth)
        
        assert ws.hass == mock_hass
        assert ws.auth == mock_auth
        assert ws.running is False
        assert ws.reconnect_attempts == 0
        assert ws.max_reconnect_attempts == 10
        
        print("✅ RointeWebSocket class tests passed!")
        return True
    except Exception as e:
        print(f"❌ RointeWebSocket test failed: {e}")
        return False

def test_climate_entity():
    """Test RointeHeater class."""
    print("\n🧪 Testing RointeHeater class...")
    
    try:
        from rointe.climate import RointeHeater, HVAC_MODES, PRESET_MODES
        
        # Mock Home Assistant and WebSocket
        mock_hass = MagicMock()
        mock_ws = MagicMock()
        
        heater = RointeHeater(mock_hass, mock_ws, "test_device", "Test Heater")
        
        # Test basic properties
        assert heater.device_id == "test_device"
        assert heater.name == "Test Heater"
        assert heater.unique_id == "rointe_test_device"
        assert heater.temperature_unit == "°C"
        assert heater.hvac_modes == HVAC_MODES
        assert heater.preset_modes == PRESET_MODES
        assert heater.available is True
        
        # Test temperature ranges
        heater._hvac_mode = "heat"
        assert heater.min_temp == 15.0
        assert heater.max_temp == 35.0
        
        heater._hvac_mode = "off"
        assert heater.min_temp == 5.0
        assert heater.max_temp == 7.0
        
        # Test device info
        device_info = heater.device_info
        assert device_info["identifiers"] == {("rointe", "test_device")}
        assert device_info["name"] == "Test Heater"
        assert device_info["manufacturer"] == "Rointe"
        
        print("✅ RointeHeater class tests passed!")
        return True
    except Exception as e:
        print(f"❌ RointeHeater test failed: {e}")
        return False

def test_config_flow():
    """Test RointeConfigFlow class."""
    print("\n🧪 Testing RointeConfigFlow class...")
    
    try:
        from rointe.config_flow import RointeConfigFlow
        
        config_flow = RointeConfigFlow()
        
        # Test email validation
        assert config_flow._is_valid_email("test@example.com")
        assert config_flow._is_valid_email("user.name+tag@domain.co.uk")
        assert not config_flow._is_valid_email("invalid-email")
        assert not config_flow._is_valid_email("@domain.com")
        assert not config_flow._is_valid_email("user@")
        
        print("✅ RointeConfigFlow class tests passed!")
        return True
    except Exception as e:
        print(f"❌ RointeConfigFlow test failed: {e}")
        return False

def test_constants():
    """Test constants and configuration."""
    print("\n🧪 Testing constants...")
    
    try:
        from rointe.const import DOMAIN, PLATFORMS
        from rointe.climate import HVAC_MODES, PRESET_MODES
        
        assert DOMAIN == "rointe"
        assert PLATFORMS == ["climate"]
        assert len(HVAC_MODES) == 4  # OFF, HEAT, AUTO, HEAT_COOL
        assert len(PRESET_MODES) == 3  # NONE, COMFORT, ECO
        
        print("✅ Constants tests passed!")
        return True
    except Exception as e:
        print(f"❌ Constants test failed: {e}")
        return False

async def test_async_functionality():
    """Test async functionality with mocks."""
    print("\n🧪 Testing async functionality...")
    
    try:
        from rointe.climate import RointeHeater
        
        # Mock Home Assistant and WebSocket
        mock_hass = MagicMock()
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()
        
        heater = RointeHeater(mock_hass, mock_ws, "test_device", "Test Heater")
        
        # Test temperature setting
        await heater.async_set_temperature(temperature=21.0)
        mock_ws.send.assert_called_once()
        
        # Test HVAC mode setting
        await heater.async_set_hvac_mode("heat")
        mock_ws.send.assert_called()
        
        # Test preset mode setting
        await heater.async_set_preset_mode("comfort")
        mock_ws.send.assert_called()
        
        print("✅ Async functionality tests passed!")
        return True
    except Exception as e:
        print(f"❌ Async functionality test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Rointe Integration Quick Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_auth_class,
        test_api_class,
        test_websocket_class,
        test_climate_entity,
        test_config_flow,
        test_constants,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    # Run async test
    try:
        if asyncio.run(test_async_functionality()):
            passed += 1
        total += 1
    except Exception as e:
        print(f"❌ Async test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Integration is ready for testing.")
        print("\nNext steps:")
        print("1. Run: python test_setup.py")
        print("2. Choose Docker-based Home Assistant setup")
        print("3. Test with real Rointe devices")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
