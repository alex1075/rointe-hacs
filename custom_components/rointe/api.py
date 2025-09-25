"""
Rointe API Module

Handles REST API calls using the dual authentication system.
Uses REST token for all API operations.
"""

import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://rointenexa.com/api"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

class RointeAPIError(Exception):
    """Base exception for Rointe API errors."""
    pass

class RointeAuthenticationError(RointeAPIError):
    """Authentication failed."""
    pass

class RointeNetworkError(RointeAPIError):
    """Network connectivity error."""
    pass

class RointeAPI:
    def __init__(self, auth):
        """Initialize API client with authentication handler"""
        self.auth = auth
        self.session: Optional[aiohttp.ClientSession] = None
        _LOGGER.debug("Initialized RointeAPI with dual authentication")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def _get(self, path: str, retry_count: int = 0) -> Dict[str, Any]:
        """Make GET request with REST token authentication and retry logic."""
        try:
            # Get valid REST token from auth handler
            token = await self.auth.async_rest_token()
            headers = {"token": token}
            url = f"{API_BASE}{path}"
            
            session = await self._get_session()
            
            _LOGGER.debug("Making REST API request: GET %s", path)
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOGGER.debug("REST API request successful: GET %s", path)
                    return data
                elif resp.status == 401:
                    _LOGGER.error("Authentication failed for REST API request: GET %s", path)
                    # Token might be expired, try to refresh
                    try:
                        await self.auth.async_login_rest()
                        token = await self.auth.async_rest_token()
                        headers = {"token": token}
                        
                        # Retry once with new token
                        async with session.get(url, headers=headers) as retry_resp:
                            if retry_resp.status == 200:
                                data = await retry_resp.json()
                                _LOGGER.debug("REST API request successful after token refresh: GET %s", path)
                                return data
                            else:
                                raise RointeAuthenticationError(f"Authentication failed even after refresh: {retry_resp.status}")
                    except Exception as e:
                        raise RointeAuthenticationError(f"Authentication failed: {e}")
                        
                elif resp.status >= 500:
                    # Server error - retry
                    _LOGGER.warning("Server error %d for GET %s, attempt %d/%d", 
                                  resp.status, path, retry_count + 1, MAX_RETRIES)
                    if retry_count < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                        return await self._get(path, retry_count + 1)
                    else:
                        raise RointeAPIError(f"Server error after {MAX_RETRIES} retries: {resp.status}")
                else:
                    error_text = await resp.text()
                    _LOGGER.error("REST API request failed: GET %s -> %d: %s", path, resp.status, error_text)
                    raise RointeAPIError(f"REST API request failed: {resp.status} - {error_text}")
                    
        except aiohttp.ClientError as e:
            _LOGGER.warning("Network error for GET %s, attempt %d/%d: %s", 
                          path, retry_count + 1, MAX_RETRIES, e)
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                return await self._get(path, retry_count + 1)
            else:
                raise RointeNetworkError(f"Network error after {MAX_RETRIES} retries: {e}")
        except Exception as e:
            if isinstance(e, (RointeAPIError, RointeAuthenticationError)):
                raise
            _LOGGER.error("Unexpected error for GET %s: %s", path, e)
            raise RointeAPIError(f"Unexpected error: {e}")

    async def list_devices(self) -> List[Dict[str, str]]:
        """Discover all devices using REST API authentication."""
        devices = []
        try:
            _LOGGER.info("Starting device discovery with REST API authentication")
            
            # Ensure we have valid REST authentication
            await self.auth.async_login_rest()
            
            # Get installations
            installations_response = await self._get("/installations")
            
            # Extract installations from nested 'data' key
            if isinstance(installations_response, dict) and "data" in installations_response:
                installations = installations_response["data"]
            else:
                installations = installations_response
                
            if not isinstance(installations, list):
                _LOGGER.error("Invalid installations response format: %s", type(installations))
                raise RointeAPIError("Invalid installations response format")
            
            _LOGGER.debug("Found %d installations", len(installations))
            
            # Process each installation
            for i, inst in enumerate(installations):
                try:
                    if not isinstance(inst, dict):
                        _LOGGER.warning("Invalid installation format at index %d", i)
                        continue
                        
                    zones = inst.get("zones", [])
                    if not isinstance(zones, list):
                        _LOGGER.warning("Invalid zones format for installation %d", i)
                        continue
                    
                    _LOGGER.debug("Processing installation %d with %d zones", i, len(zones))
                    
                    # Process each zone (zones now contain devices directly)
                    for zone in zones:
                        try:
                            if not isinstance(zone, dict):
                                _LOGGER.warning("Invalid zone format: %s", zone)
                                continue
                                
                            zone_id = zone.get("id")
                            zone_name = zone.get("name", f"Zone {zone_id}")
                            devices_list = zone.get("devices", [])
                            
                            if not isinstance(devices_list, list):
                                _LOGGER.warning("Invalid devices format for zone %s", zone_id)
                                continue
                            
                            _LOGGER.debug("Zone %s (%s) has %d devices", zone_id, zone_name, len(devices_list))
                            
                            # Process each device
                            for device in devices_list:
                                try:
                                    if not isinstance(device, dict):
                                        _LOGGER.warning("Invalid device format in zone %s", zone_id)
                                        continue
                                        
                                    device_id = device.get("id")
                                    if not device_id:
                                        _LOGGER.warning("Device missing ID in zone %s", zone_id)
                                        continue
                                    
                                    device_name = device.get("name", device_id)
                                    device_info = {
                                        "id": device_id,
                                        "name": device_name,
                                        "zone": zone_name,
                                        "model": device.get("model"),
                                        "power": device.get("power"),
                                        "version": device.get("version"),
                                        "type": device.get("type"),
                                        "serialNumber": device.get("serialNumber"),
                                        "mac": device.get("mac"),
                                        "deviceStatus": device.get("deviceStatus"),
                                    }
                                    devices.append(device_info)
                                    _LOGGER.debug("Added device: %s (%s) in zone %s - Model: %s, Power: %sW", 
                                                device_id, device_name, zone_name, 
                                                device.get("model", "Unknown"), device.get("power", "Unknown"))
                                    
                                except Exception as e:
                                    _LOGGER.error("Error processing device in zone %s: %s", zone_id, e)
                                    continue
                                    
                        except Exception as e:
                            _LOGGER.error("Error processing zone %s: %s", zone_id, e)
                            continue
                            
                except Exception as e:
                    _LOGGER.error("Error processing installation %d: %s", i, e)
                    continue
            
            _LOGGER.info("Device discovery completed: found %d devices", len(devices))
            return devices
            
        except Exception as e:
            _LOGGER.error("Device discovery failed: %s", e)
            raise

    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get current status of a specific device."""
        try:
            _LOGGER.debug("Getting status for device: %s", device_id)
            return await self._get(f"/devices/{device_id}/status")
        except Exception as e:
            _LOGGER.error("Failed to get status for device %s: %s", device_id, e)
            raise

    async def set_device_temperature(self, device_id: str, temperature: float) -> bool:
        """Set target temperature for a device."""
        try:
            _LOGGER.debug("Setting temperature for device %s to %s°C", device_id, temperature)
            
            # Get valid REST token
            token = await self.auth.async_rest_token()
            headers = {
                "token": token,
                "Content-Type": "application/json"
            }
            
            url = f"{API_BASE}/devices/{device_id}/temperature"
            data = {"temperature": temperature}
            
            session = await self._get_session()
            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    _LOGGER.debug("Temperature set successfully for device %s", device_id)
                    return True
                else:
                    error_text = await resp.text()
                    _LOGGER.error("Failed to set temperature for device %s: %d - %s", 
                                device_id, resp.status, error_text)
                    return False
                    
        except Exception as e:
            _LOGGER.error("Error setting temperature for device %s: %s", device_id, e)
            return False

    async def set_device_power(self, device_id: str, power: bool) -> bool:
        """Set power state for a device."""
        try:
            _LOGGER.debug("Setting power for device %s to %s", device_id, power)
            
            # Get valid REST token
            token = await self.auth.async_rest_token()
            headers = {
                "token": token,
                "Content-Type": "application/json"
            }
            
            url = f"{API_BASE}/devices/{device_id}/power"
            data = {"power": power}
            
            session = await self._get_session()
            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    _LOGGER.debug("Power set successfully for device %s", device_id)
                    return True
                else:
                    error_text = await resp.text()
                    _LOGGER.error("Failed to set power for device %s: %d - %s", 
                                device_id, resp.status, error_text)
                    return False
                    
        except Exception as e:
            _LOGGER.error("Error setting power for device %s: %s", device_id, e)
            return False