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
        self.auth = auth
        self.session: Optional[aiohttp.ClientSession] = None

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
        """Make GET request with retry logic and error handling."""
        try:
            token = await self.auth.async_refresh()
            headers = {"token": token}
            url = f"{API_BASE}{path}"
            
            session = await self._get_session()
            
            _LOGGER.debug("Making API request: GET %s", path)
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOGGER.debug("API request successful: GET %s", path)
                    return data
                elif resp.status == 401:
                    _LOGGER.error("Authentication failed for API request: GET %s", path)
                    raise RointeAuthenticationError(f"Authentication failed: {resp.status}")
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
                    _LOGGER.error("API request failed: GET %s -> %d: %s", path, resp.status, error_text)
                    raise RointeAPIError(f"API request failed: {resp.status} - {error_text}")
                    
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
        """Discover all devices with enhanced error handling."""
        devices = []
        try:
            _LOGGER.info("Starting device discovery")
            
            # Get installations
            installations = await self._get("/installations")
            if not isinstance(installations, list):
                _LOGGER.error("Invalid installations response format")
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
                    
                    # Process each zone
                    for zone_id in zones:
                        try:
                            if not isinstance(zone_id, str):
                                _LOGGER.warning("Invalid zone ID format: %s", zone_id)
                                continue
                                
                            zone = await self._get(f"/zones/{zone_id}")
                            if not isinstance(zone, dict):
                                _LOGGER.warning("Invalid zone response for zone %s", zone_id)
                                continue
                            
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