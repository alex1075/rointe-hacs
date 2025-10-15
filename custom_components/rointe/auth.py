import aiohttp
import logging
from typing import Optional
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

# Firebase configuration
FIREBASE_API_KEY = "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY"
FIREBASE_AUTH_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_TOKEN_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"

# Rointe REST API configuration
ROINTE_API_BASE = "https://rointenexa.com"
ROINTE_LOGIN_URL = f"{ROINTE_API_BASE}/api/user/login"
ROINTE_INSTALLATIONS_URL = f"{ROINTE_API_BASE}/api/installations"

# Token expiration buffer
TOKEN_EXPIRY_BUFFER = timedelta(minutes=5)


class RointeAuthError(Exception):
    pass


class RointeRestAuthError(RointeAuthError):
    pass


class RointeFirebaseAuthError(RointeAuthError):
    pass


class RointeAuth:
    """Handles dual authentication + installation_default cookie via REST requests"""

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None

        # REST tokens
        self._rest_token: Optional[str] = None
        self._rest_token_expiry: Optional[datetime] = None
        self._rest_refresh_token: Optional[str] = None
        self._user_id: Optional[str] = None

        # Firebase tokens
        self._firebase_id_token: Optional[str] = None
        self._firebase_refresh_token: Optional[str] = None
        self._firebase_token_expiry: Optional[datetime] = None

        # installation_default cookie
        self.installation_default: Optional[str] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _get_session(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def async_login_rest(self) -> bool:
        """Login REST API, store tokens + installation_default cookie via direct requests"""
        try:
            session = await self._get_session()

            # Step 1: Login and get REST token
            login_payload = {
                "email": self.email,
                "password": self.password,
                "push": "",  # optional if not needed
                "migrate": False
            }
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Origin": "https://rointenexa.com",
                "Referer": "https://rointenexa.com/login",
            }

            async with session.post(ROINTE_LOGIN_URL, json=login_payload, headers=headers) as resp:
                resp_data = await resp.json()
                if resp.status != 200:
                    raise RointeRestAuthError(f"REST login failed: {resp_data}")

                data = resp_data.get("data", {})
                self._rest_token = data.get("token")
                self._rest_refresh_token = data.get("refreshToken")
                self._user_id = data.get("user", {}).get("id")

                # Step 2: Fetch installation_default via /installations
                install_headers = {"token": self._rest_token}
                async with session.get(ROINTE_INSTALLATIONS_URL, headers=install_headers) as inst_resp:
                    if inst_resp.status != 200:
                        raise RointeRestAuthError(f"Failed to fetch installations: {await inst_resp.text()}")
                    # Read installation_default from Set-Cookie
                    cookies = inst_resp.cookies
                    self.installation_default = cookies.get("installation_default").value if cookies.get("installation_default") else None

                    if not self.installation_default:
                        # fallback: pick first installation ID from data
                        inst_data = await inst_resp.json()
                        first_install = inst_data.get("data", [{}])[0]
                        self.installation_default = first_install.get("id")

            # Set token expiry
            expires_in = data.get("expires_in", 3600)
            self._rest_token_expiry = datetime.now() + timedelta(seconds=expires_in)

            _LOGGER.debug(f"REST login successful, installation_default={self.installation_default}")
            return True

        except Exception as e:
            _LOGGER.error(f"REST login error: {e}")
            raise RointeRestAuthError(str(e))

    async def async_rest_token(self) -> str:
        """Get REST token, refresh if expired"""
        if not self._rest_token or not self._rest_token_expiry or datetime.now() + TOKEN_EXPIRY_BUFFER >= self._rest_token_expiry:
            await self.async_login_rest()
        return self._rest_token

    async def async_rest_request(self, method: str, url: str, **kwargs) -> dict:
        """Make a REST request, automatically adding token + installation_default"""
        await self.async_rest_token()

        session = await self._get_session()
        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": f"Bearer {self._rest_token}",
        })
        if self.installation_default:
            headers["Cookie"] = f"installation_default={self.installation_default}"

        async with session.request(method, url, headers=headers, **kwargs) as response:
            if response.status in (401, 403):
                # Refresh token & retry once
                await self.async_login_rest()
                headers["Authorization"] = f"Bearer {self._rest_token}"
                if self.installation_default:
                    headers["Cookie"] = f"installation_default={self.installation_default}"
                async with session.request(method, url, headers=headers, **kwargs) as retry_resp:
                    return await retry_resp.json()
            return await response.json()

    async def async_login_firebase(self) -> bool:
        """Login Firebase using user_id"""
        if not self._user_id:
            raise RointeFirebaseAuthError("User ID required")

        session = await self._get_session()
        firebase_email = f"{self._user_id}@rointe.com"
        firebase_password = self._user_id
        firebase_data = {"email": firebase_email, "password": firebase_password, "returnSecureToken": True}

        async with session.post(FIREBASE_AUTH_URL, json=firebase_data) as response:
            data = await response.json()
            if response.status != 200:
                raise RointeFirebaseAuthError(f"Firebase login failed: {data}")
            self._firebase_id_token = data.get("idToken")
            self._firebase_refresh_token = data.get("refreshToken")
            expires_in = int(data.get("expiresIn", 3600))
            self._firebase_token_expiry = datetime.now() + timedelta(seconds=expires_in)
            return True

    async def async_firebase_token(self) -> str:
        """Get Firebase token, refresh if expired"""
        if not self._firebase_id_token or not self._firebase_token_expiry or datetime.now() + TOKEN_EXPIRY_BUFFER >= self._firebase_token_expiry:
            await self.async_login_firebase()
        return self._firebase_id_token
