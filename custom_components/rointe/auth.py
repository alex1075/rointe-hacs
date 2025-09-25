import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

_LOGGER = logging.getLogger(__name__)

FIREBASE_API_KEY = "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY"
REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

class RointeAuthenticationError(Exception):
    """Authentication failed."""
    pass

class RointeAuth:
    def __init__(self, hass, refresh_token: str):
        self.hass = hass
        self.refresh_token = refresh_token
        self.id_token: Optional[str] = None
        self.expiry = datetime.utcnow()
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

    async def async_refresh(self, retry_count: int = 0) -> str:
        """Refresh the ID token with enhanced error handling."""
        # Return cached token if still valid
        if self.id_token and datetime.utcnow() < self.expiry:
            _LOGGER.debug("Using cached ID token, expires %s", self.expiry)
            return self.id_token

        try:
            _LOGGER.debug("Refreshing ID token, attempt %d/%d", retry_count + 1, MAX_RETRIES)
            
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }
            
            session = await self._get_session()
            
            async with session.post(REFRESH_URL, data=payload) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        
                        # Validate response format
                        if not isinstance(data, dict):
                            raise RointeAuthenticationError("Invalid token response format")
                        
                        required_fields = ["id_token", "refresh_token", "expires_in"]
                        for field in required_fields:
                            if field not in data:
                                raise RointeAuthenticationError(f"Missing field in token response: {field}")
                        
                        # Update tokens
                        self.id_token = data["id_token"]
                        self.refresh_token = data["refresh_token"]
                        
                        # Calculate expiry with buffer
                        expires_in = int(data["expires_in"])
                        if expires_in <= 0:
                            raise RointeAuthenticationError("Invalid token expiry time")
                        
                        self.expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                        
                        _LOGGER.info("Successfully refreshed ID token, expires %s", self.expiry)
                        return self.id_token
                        
                    except (ValueError, KeyError, TypeError) as e:
                        _LOGGER.error("Invalid token response format: %s", e)
                        raise RointeAuthenticationError(f"Invalid token response: {e}")
                
                elif resp.status == 400:
                    error_text = await resp.text()
                    _LOGGER.error("Bad request during token refresh: %s", error_text)
                    
                    # Check for specific Firebase error types
                    if "INVALID_REFRESH_TOKEN" in error_text or "TOKEN_EXPIRED" in error_text:
                        raise RointeAuthenticationError("Refresh token is invalid or expired - please reconfigure the integration")
                    elif "USER_DISABLED" in error_text:
                        raise RointeAuthenticationError("User account has been disabled")
                    else:
                        raise RointeAuthenticationError(f"Authentication failed: {error_text}")
                
                elif resp.status == 401:
                    error_text = await resp.text()
                    _LOGGER.error("Unauthorized during token refresh: %s", error_text)
                    raise RointeAuthenticationError("Authentication failed - invalid credentials")
                
                elif resp.status >= 500:
                    # Server error - retry
                    _LOGGER.warning("Server error %d during token refresh, attempt %d/%d", 
                                  resp.status, retry_count + 1, MAX_RETRIES)
                    if retry_count < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                        return await self.async_refresh(retry_count + 1)
                    else:
                        raise RointeAuthenticationError(f"Server error after {MAX_RETRIES} retries: {resp.status}")
                
                else:
                    error_text = await resp.text()
                    _LOGGER.error("Token refresh failed with status %d: %s", resp.status, error_text)
                    raise RointeAuthenticationError(f"Token refresh failed: {resp.status} - {error_text}")
                    
        except aiohttp.ClientError as e:
            _LOGGER.warning("Network error during token refresh, attempt %d/%d: %s", 
                          retry_count + 1, MAX_RETRIES, e)
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                return await self.async_refresh(retry_count + 1)
            else:
                raise RointeAuthenticationError(f"Network error after {MAX_RETRIES} retries: {e}")
        
        except RointeAuthenticationError:
            raise
        
        except Exception as e:
            _LOGGER.error("Unexpected error during token refresh: %s", e)
            raise RointeAuthenticationError(f"Unexpected error: {e}")

    def is_token_valid(self) -> bool:
        """Check if the current token is still valid."""
        return self.id_token is not None and datetime.utcnow() < self.expiry

    def get_token_info(self) -> dict:
        """Get information about the current token state."""
        return {
            "has_token": self.id_token is not None,
            "is_valid": self.is_token_valid(),
            "expires_at": self.expiry.isoformat() if self.expiry else None,
            "expires_in_seconds": max(0, int((self.expiry - datetime.utcnow()).total_seconds())) if self.expiry else 0
        }