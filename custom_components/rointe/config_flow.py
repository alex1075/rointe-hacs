import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
import aiohttp

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

FIREBASE_API_KEY = "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY"
SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"

class RointeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rointe Nexa."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            try:
                refresh_token = await self._async_login(self.hass, email, password)
                return self.async_create_entry(
                    title="Rointe Nexa",
                    data={"refresh_token": refresh_token, "email": email},
                )
            except Exception as e:
                _LOGGER.error("Login failed: %s", e)
                errors["base"] = "auth"

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _async_login(self, hass: HomeAssistant, email: str, password: str) -> str:
        """Login to Rointe (Firebase) and return refresh_token."""
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(SIGNIN_URL, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Auth failed {resp.status}: {text}")
                data = await resp.json()
                _LOGGER.debug("Login response: %s", data)
                return data["refreshToken"]