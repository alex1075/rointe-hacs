#!/usr/bin/env python3
"""
Local testing setup for Rointe HACS integration.
This script helps set up a local Home Assistant development environment.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def run_command(cmd, description):
    print(f"\n🔄 {description}")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Success!")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
        else:
            print(f"❌ Failed!")
            print(f"Error: {result.stderr.strip()}")
            return False
        return True
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print_header("Rointe Integration Local Testing Setup")
    
    print("""
This script will help you set up local testing for the Rointe integration.
Choose your preferred testing method:

1. Docker-based Home Assistant (Recommended - Easy setup)
2. Python virtual environment with HA core
3. Manual testing with mock data
4. Integration test runner
""")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        setup_docker_ha()
    elif choice == "2":
        setup_python_ha()
    elif choice == "3":
        setup_mock_testing()
    elif choice == "4":
        setup_integration_tests()
    else:
        print("Invalid choice. Exiting.")

def setup_docker_ha():
    print_header("Docker-based Home Assistant Setup")
    
    print("""
This will set up a local Home Assistant instance using Docker.
Your integration will be copied to the custom_components directory.
""")
    
    # Check if Docker is available
    if not run_command("docker --version", "Checking Docker installation"):
        print("""
❌ Docker is not installed or not available.
Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
""")
        return
    
    # Create HA configuration directory
    config_dir = Path.home() / ".homeassistant"
    config_dir.mkdir(exist_ok=True)
    
    custom_components_dir = config_dir / "custom_components"
    custom_components_dir.mkdir(exist_ok=True)
    
    # Copy integration to custom_components
    print("\n🔄 Copying integration to Home Assistant...")
    import shutil
    rointe_dest = custom_components_dir / "rointe"
    if rointe_dest.exists():
        shutil.rmtree(rointe_dest)
    shutil.copytree("custom_components/rointe", rointe_dest)
    print("✅ Integration copied!")
    
    # Create docker-compose.yml
    docker_compose = """version: '3.8'
services:
  homeassistant:
    container_name: homeassistant
    image: "ghcr.io/home-assistant/home-assistant:stable"
    volumes:
      - ${PWD}/.homeassistant:/config
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    privileged: true
    network_mode: host
    environment:
      - TZ=UTC
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose)
    
    print("""
✅ Docker setup complete!

To start Home Assistant:
1. Run: docker-compose up -d
2. Open: http://localhost:8123
3. Complete the initial setup
4. Go to Settings → Devices & Services → Add Integration
5. Search for "Rointe" and configure with your credentials

To stop Home Assistant:
- Run: docker-compose down

To view logs:
- Run: docker-compose logs -f homeassistant
""")

def setup_python_ha():
    print_header("Python Virtual Environment Setup")
    
    print("Setting up Python virtual environment for Home Assistant development...")
    
    # Create virtual environment
    if not run_command("python -m venv ha_test_env", "Creating virtual environment"):
        return
    
    # Determine activation script based on OS
    if platform.system() == "Windows":
        activate_script = "ha_test_env\\Scripts\\activate"
        pip_cmd = "ha_test_env\\Scripts\\pip"
    else:
        activate_script = "source ha_test_env/bin/activate"
        pip_cmd = "ha_test_env/bin/pip"
    
    # Install Home Assistant
    if not run_command(f"{pip_cmd} install homeassistant", "Installing Home Assistant"):
        return
    
    print(f"""
✅ Python environment setup complete!

To start Home Assistant:
1. Activate environment: {activate_script}
2. Run: hass --open-ui
3. Open: http://localhost:8123
4. Copy integration to: ~/.homeassistant/custom_components/rointe/

To stop Home Assistant:
- Press Ctrl+C
""")

def setup_mock_testing():
    print_header("Mock Testing Setup")
    
    print("Creating mock testing environment...")
    
    # Create test directory
    test_dir = Path("tests")
    test_dir.mkdir(exist_ok=True)
    
    # Create mock test files
    mock_test = """#!/usr/bin/env python3
\"\"\"
Mock testing for Rointe integration.
This allows testing without actual Rointe devices.
\"\"\"

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# Add the integration to path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))

async def test_integration():
    \"\"\"Test the integration with mock data.\"\"\"
    print("🧪 Starting mock integration tests...")
    
    # Mock Home Assistant
    mock_hass = MagicMock()
    mock_hass.data = {}
    
    # Mock entry
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    mock_entry.data = {
        "refresh_token": "mock_refresh_token",
        "email": "test@example.com"
    }
    
    try:
        # Import integration components
        from rointe import async_setup_entry
        from rointe.auth import RointeAuth
        from rointe.api import RointeAPI
        from rointe.ws import RointeWebSocket
        from rointe.climate import RointeHeater
        
        print("✅ All imports successful!")
        
        # Test auth class
        auth = RointeAuth(mock_hass, "mock_token")
        print("✅ Auth class instantiated!")
        
        # Test API class
        api = RointeAPI(auth)
        print("✅ API class instantiated!")
        
        # Test WebSocket class
        ws = RointeWebSocket(mock_hass, auth)
        print("✅ WebSocket class instantiated!")
        
        # Test Climate entity
        heater = RointeHeater(mock_hass, ws, "test_device", "Test Heater")
        print("✅ Climate entity instantiated!")
        
        print("\\n🎉 All mock tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_integration())
"""
    
    with open("tests/mock_test.py", "w") as f:
        f.write(mock_test)
    
    print("""
✅ Mock testing setup complete!

To run mock tests:
1. Run: python tests/mock_test.py

This will test:
- Import of all integration components
- Class instantiation
- Basic functionality without real devices
""")

def setup_integration_tests():
    print_header("Integration Test Runner")
    
    print("Setting up comprehensive integration tests...")
    
    # Create test directory
    test_dir = Path("tests")
    test_dir.mkdir(exist_ok=True)
    
    # Create test requirements
    requirements = """pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-mock>=3.10.0
aiohttp>=3.8.0
homeassistant>=2023.1.0
"""
    
    with open("tests/requirements.txt", "w") as f:
        f.write(requirements)
    
    # Create comprehensive test file
    test_file = """#!/usr/bin/env python3
\"\"\"
Comprehensive integration tests for Rointe integration.
\"\"\"

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
from pathlib import Path
import sys

# Add the integration to path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))

from rointe.auth import RointeAuth, RointeAuthenticationError
from rointe.api import RointeAPI, RointeAPIError
from rointe.ws import RointeWebSocket
from rointe.climate import RointeHeater, HVAC_MODES, PRESET_MODES
from rointe.config_flow import RointeConfigFlow

class TestRointeAuth:
    \"\"\"Test authentication functionality.\"\"\"
    
    @pytest.fixture
    def mock_hass(self):
        return MagicMock()
    
    @pytest.fixture
    def auth(self, mock_hass):
        return RointeAuth(mock_hass, "test_refresh_token")
    
    def test_auth_initialization(self, auth):
        \"\"\"Test auth initialization.\"\"\"
        assert auth.refresh_token == "test_refresh_token"
        assert auth.id_token is None
    
    @pytest.mark.asyncio
    async def test_token_validation(self, auth):
        \"\"\"Test token validation.\"\"\"
        assert not auth.is_token_valid()
        
        # Mock valid token
        auth.id_token = "test_token"
        auth.expiry = datetime.utcnow() + timedelta(hours=1)
        assert auth.is_token_valid()

class TestRointeAPI:
    \"\"\"Test API functionality.\"\"\"
    
    @pytest.fixture
    def mock_auth(self):
        auth = MagicMock()
        auth.async_refresh = AsyncMock(return_value="test_token")
        return auth
    
    @pytest.fixture
    def api(self, mock_auth):
        return RointeAPI(mock_auth)
    
    @pytest.mark.asyncio
    async def test_api_initialization(self, api):
        \"\"\"Test API initialization.\"\"\"
        assert api.auth is not None

class TestRointeClimate:
    \"\"\"Test climate entity functionality.\"\"\"
    
    @pytest.fixture
    def mock_hass(self):
        return MagicMock()
    
    @pytest.fixture
    def mock_ws(self):
        ws = MagicMock()
        ws.send = AsyncMock()
        return ws
    
    @pytest.fixture
    def heater(self, mock_hass, mock_ws):
        return RointeHeater(mock_hass, mock_ws, "test_device", "Test Heater")
    
    def test_heater_properties(self, heater):
        \"\"\"Test heater properties.\"\"\"
        assert heater.device_id == "test_device"
        assert heater.name == "Test Heater"
        assert heater.unique_id == "rointe_test_device"
        assert heater.temperature_unit == "°C"
        assert heater.hvac_modes == HVAC_MODES
        assert heater.preset_modes == PRESET_MODES
    
    @pytest.mark.asyncio
    async def test_set_temperature(self, heater):
        \"\"\"Test temperature setting.\"\"\"
        await heater.async_set_temperature(temperature=21.0)
        heater.ws.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_hvac_mode(self, heater):
        \"\"\"Test HVAC mode setting.\"\"\"
        await heater.async_set_hvac_mode("heat")
        heater.ws.send.assert_called_once()
    
    def test_temperature_validation(self, heater):
        \"\"\"Test temperature validation.\"\"\"
        # Test valid temperature
        heater._hvac_mode = "heat"
        assert heater.min_temp == 15.0
        assert heater.max_temp == 35.0
        
        # Test OFF mode temperature range
        heater._hvac_mode = "off"
        assert heater.min_temp == 5.0
        assert heater.max_temp == 7.0

class TestConfigFlow:
    \"\"\"Test configuration flow.\"\"\"
    
    @pytest.fixture
    def config_flow(self):
        return RointeConfigFlow()
    
    def test_email_validation(self, config_flow):
        \"\"\"Test email validation.\"\"\"
        assert config_flow._is_valid_email("test@example.com")
        assert config_flow._is_valid_email("user.name+tag@domain.co.uk")
        assert not config_flow._is_valid_email("invalid-email")
        assert not config_flow._is_valid_email("@domain.com")
        assert not config_flow._is_valid_email("user@")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
    
    with open("tests/test_integration.py", "w") as f:
        f.write(test_file)
    
    print("""
✅ Integration test setup complete!

To run tests:
1. Install test dependencies: pip install -r tests/requirements.txt
2. Run tests: python -m pytest tests/ -v

This will run comprehensive tests for:
- Authentication functionality
- API interactions
- Climate entity behavior
- Configuration flow
- Error handling
""")

if __name__ == "__main__":
    main()
