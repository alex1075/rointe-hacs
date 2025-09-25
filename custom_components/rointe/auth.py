"""
Rointe Authentication Module

Handles dual authentication system:
1. Rointe REST API authentication for API calls
2. Firebase authentication for WebSocket connection
"""

import asyncio
import aiohttp
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

# Firebase configuration
FIREBASE_API_KEY = "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY"
FIREBASE_AUTH_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_TOKEN_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"

# Rointe REST API configuration
ROINTE_API_BASE = "https://rointenexa.com"
ROINTE_LOGIN_URL = f"{ROINTE_API_BASE}/api/user/login"

# Token expiration buffer (refresh 5 minutes before expiry)
TOKEN_EXPIRY_BUFFER = timedelta(minutes=5)


class RointeAuthError(Exception):
    """Base exception for Rointe authentication errors"""
    pass


class RointeRestAuthError(RointeAuthError):
    """Exception for REST API authentication errors"""
    pass


class RointeFirebaseAuthError(RointeAuthError):
    """Exception for Firebase authentication errors"""
    pass


class RointeAuth:
    """Handles dual authentication for Rointe integration"""
    
    def __init__(self, email: str, password: str):
        """Initialize authentication with email and password"""
        self.email = email
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None
        
        # REST API tokens
        self._rest_token: Optional[str] = None
        self._rest_token_expiry: Optional[datetime] = None
        self._user_id: Optional[str] = None
        
        # Firebase tokens
        self._firebase_id_token: Optional[str] = None
        self._firebase_refresh_token: Optional[str] = None
        self._firebase_token_expiry: Optional[datetime] = None
        
        _LOGGER.debug(f"Initialized RointeAuth for email: {email}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def async_login_rest(self) -> bool:
        """
        Login to Rointe REST API and obtain REST token
        
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            _LOGGER.debug("Attempting REST API login")
            
            session = await self._get_session()
            
            # Prepare login payload
            login_data = {
                "email": self.email,
                "password": self.password
            }
            
            # Make login request
            async with session.post(
                ROINTE_LOGIN_URL,
                json=login_data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    # Handle nested response structure from REST API
                    data = response_data.get("data", {})
                    self._rest_token = data.get("token")
                    self._rest_refresh_token = data.get("refreshToken")
                    
                    user_info = data.get("user", {})
                    self._user_id = user_info.get("id")
                    
                    # Set token expiry (default to 1 hour if not provided)
                    expires_in = data.get("expires_in", 3600)
                    self._rest_token_expiry = datetime.now() + timedelta(seconds=expires_in)
                    
                    _LOGGER.debug(f"REST login successful, user_id: {self._user_id}")
                    return True
                    
                elif response.status == 401:
                    error_msg = response_data.get("error", {}).get("message", "Invalid credentials")
                    _LOGGER.error(f"REST login failed: {error_msg}")
                    raise RointeRestAuthError(f"Invalid credentials: {error_msg}")
                    
                else:
                    error_msg = response_data.get("error", {}).get("message", f"HTTP {response.status}")
                    _LOGGER.error(f"REST login failed: {error_msg}")
                    raise RointeRestAuthError(f"Login failed: {error_msg}")
                    
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Network error during REST login: {e}")
            raise RointeRestAuthError(f"Network error: {e}")
        except Exception as e:
            _LOGGER.error(f"Unexpected error during REST login: {e}")
            raise RointeRestAuthError(f"Login error: {e}")
    
    async def async_login_firebase(self) -> bool:
        """
        Login to Firebase using user_id as credentials
        
        Returns:
            bool: True if login successful, False otherwise
        """
        if not self._user_id:
            raise RointeFirebaseAuthError("User ID not available. REST login required first.")
        
        try:
            _LOGGER.debug("Attempting Firebase login")
            
            session = await self._get_session()
            
            # Firebase uses user_id as email and password
            firebase_email = f"{self._user_id}@rointe.com"
            firebase_password = self._user_id
            
            # Prepare Firebase login payload
            firebase_data = {
                "email": firebase_email,
                "password": firebase_password,
                "returnSecureToken": True
            }
            
            # Make Firebase login request
            async with session.post(
                FIREBASE_AUTH_URL,
                json=firebase_data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    # Extract Firebase tokens
                    self._firebase_id_token = response_data.get("idToken")
                    self._firebase_refresh_token = response_data.get("refreshToken")
                    
                    # Set token expiry
                    expires_in = int(response_data.get("expiresIn", 3600))
                    self._firebase_token_expiry = datetime.now() + timedelta(seconds=expires_in)
                    
                    _LOGGER.debug("Firebase login successful")
                    return True
                    
                elif response.status == 400:
                    error_msg = response_data.get("error", {}).get("message", "Invalid Firebase credentials")
                    _LOGGER.error(f"Firebase login failed: {error_msg}")
                    raise RointeFirebaseAuthError(f"Firebase auth failed: {error_msg}")
                    
                else:
                    error_msg = response_data.get("error", {}).get("message", f"HTTP {response.status}")
                    _LOGGER.error(f"Firebase login failed: {error_msg}")
                    raise RointeFirebaseAuthError(f"Firebase login failed: {error_msg}")
                    
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Network error during Firebase login: {e}")
            raise RointeFirebaseAuthError(f"Network error: {e}")
        except Exception as e:
            _LOGGER.error(f"Unexpected error during Firebase login: {e}")
            raise RointeFirebaseAuthError(f"Firebase login error: {e}")
    
    async def async_rest_token(self) -> str:
        """
        Get valid REST API token, refreshing if necessary
        
        Returns:
            str: Valid REST API token
        """
        # Check if token is expired or missing
        if (not self._rest_token or 
            not self._rest_token_expiry or 
            datetime.now() + TOKEN_EXPIRY_BUFFER >= self._rest_token_expiry):
            
            _LOGGER.debug("REST token expired or missing, refreshing")
            await self.async_login_rest()
        
        return self._rest_token
    
    async def async_firebase_token(self) -> str:
        """
        Get valid Firebase ID token, refreshing if necessary
        
        Returns:
            str: Valid Firebase ID token
        """
        # Check if token is expired or missing
        if (not self._firebase_id_token or 
            not self._firebase_token_expiry or 
            datetime.now() + TOKEN_EXPIRY_BUFFER >= self._firebase_token_expiry):
            
            _LOGGER.debug("Firebase token expired or missing, refreshing")
            
            # Try to refresh existing token first
            if self._firebase_refresh_token:
                try:
                    await self._async_refresh_firebase_token()
                except RointeFirebaseAuthError:
                    # Refresh failed, try full login
                    await self.async_login_firebase()
            else:
                # No refresh token, do full login
                await self.async_login_firebase()
        
        return self._firebase_id_token
    
    async def _async_refresh_firebase_token(self):
        """Refresh Firebase token using refresh token"""
        try:
            _LOGGER.debug("Refreshing Firebase token")
            
            session = await self._get_session()
            
            # Prepare refresh payload
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": self._firebase_refresh_token
            }
            
            # Make refresh request
            async with session.post(
                FIREBASE_TOKEN_URL,
                json=refresh_data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    # Update tokens
                    self._firebase_id_token = response_data.get("id_token")
                    self._firebase_refresh_token = response_data.get("refresh_token")
                    
                    # Set new expiry
                    expires_in = int(response_data.get("expires_in", 3600))
                    self._firebase_token_expiry = datetime.now() + timedelta(seconds=expires_in)
                    
                    _LOGGER.debug("Firebase token refreshed successfully")
                    
                else:
                    error_msg = response_data.get("error", {}).get("message", f"HTTP {response.status}")
                    _LOGGER.error(f"Firebase token refresh failed: {error_msg}")
                    raise RointeFirebaseAuthError(f"Token refresh failed: {error_msg}")
                    
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Network error during Firebase token refresh: {e}")
            raise RointeFirebaseAuthError(f"Network error: {e}")
        except Exception as e:
            _LOGGER.error(f"Unexpected error during Firebase token refresh: {e}")
            raise RointeFirebaseAuthError(f"Token refresh error: {e}")
    
    async def async_validate_credentials(self) -> bool:
        """
        Validate credentials by attempting REST login
        
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            await self.async_login_rest()
            return True
        except RointeRestAuthError:
            return False
        except Exception as e:
            _LOGGER.error(f"Unexpected error validating credentials: {e}")
            return False
    
    def get_user_id(self) -> Optional[str]:
        """Get the user ID from REST login"""
        return self._user_id
    
    def is_rest_token_valid(self) -> bool:
        """Check if REST token is valid and not expired"""
        return (self._rest_token is not None and 
                self._rest_token_expiry is not None and 
                datetime.now() < self._rest_token_expiry)
    
    def is_firebase_token_valid(self) -> bool:
        """Check if Firebase token is valid and not expired"""
        return (self._firebase_id_token is not None and 
                self._firebase_token_expiry is not None and 
                datetime.now() < self._firebase_token_expiry)