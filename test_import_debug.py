#!/usr/bin/env python3
"""Debug script to test sensor import issues."""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

def test_sensor_import():
    """Test importing the sensor module directly."""
    print("🔍 Testing sensor import...")
    
    try:
        # Try to import the sensor module
        import rointe.sensor
        print("✅ rointe.sensor imported successfully")
        return True
    except ImportError as e:
        print(f"❌ ImportError: {e}")
        print(f"   Error type: {type(e)}")
        print(f"   Error args: {e.args}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print(f"   Error type: {type(e)}")
        print(f"   Error args: {e.args}")
        return False

def test_individual_imports():
    """Test each import in the sensor module individually."""
    print("\n🔍 Testing individual imports...")
    
    imports_to_test = [
        "homeassistant.components.sensor.SensorEntity",
        "homeassistant.components.sensor.SensorDeviceClass", 
        "homeassistant.components.sensor.SensorStateClass",
        "homeassistant.components.sensor.SensorEntityDescription",
        "homeassistant.const.POWER_WATT",
        "homeassistant.const.ENERGY_KILO_WATT_HOUR",
        "homeassistant.const.TEMP_CELSIUS",
        "homeassistant.core.callback",
        "homeassistant.helpers.dispatcher.async_dispatcher_connect",
        "homeassistant.helpers.entity.Entity",
    ]
    
    for import_path in imports_to_test:
        try:
            # Split module and attribute
            if '.' in import_path:
                module_path, attr_name = import_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[attr_name])
                attr = getattr(module, attr_name)
                print(f"✅ {import_path} - OK")
            else:
                module = __import__(import_path)
                print(f"✅ {import_path} - OK")
        except ImportError as e:
            print(f"❌ {import_path} - ImportError: {e}")
        except AttributeError as e:
            print(f"❌ {import_path} - AttributeError: {e}")
        except Exception as e:
            print(f"❌ {import_path} - Error: {e}")

if __name__ == "__main__":
    print("🧪 Rointe Sensor Import Debug\n")
    
    # First test individual imports
    test_individual_imports()
    
    # Then test the full sensor import
    success = test_sensor_import()
    
    if not success:
        print("\n💥 Sensor import failed!")
        sys.exit(1)
    else:
        print("\n🎉 Sensor import successful!")
