import logging
import voluptuous as vol
import re
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.exceptions import HomeAssistantError
import aiohttp

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

FIREBASE_API_KEY = "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY"
SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"

# Error types for better user experience
class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
    pass

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
    pass

class InvalidCredentials(HomeAssistantError):
    """Error to indicate invalid credentials format."""
    pass

class RointeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rointe Nexa."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._email = None
        self._password = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            password = user_input[CONF_PASSWORD]

            # Validate email format
            if not self._is_valid_email(email):
                errors[CONF_EMAIL] = "invalid_email_format"
            elif not password or len(password) < 6:
                errors[CONF_PASSWORD] = "password_too_short"
            else:
                self._email = email
                self._password = password
                
                try:
                    await self.async_set_unique_id(email)
                    self._abort_if_unique_id_configured()
                    
                    refresh_token = await self._async_login(self.hass, email, password)
                    
                    return self.async_create_entry(
                        title=f"Rointe Nexa ({email})",
                        data={
                            "refresh_token": refresh_token, 
                            "email": email
                        },
                    )
                    
                except InvalidCredentials:
                    errors[CONF_EMAIL] = "invalid_credentials"
                    errors[CONF_PASSWORD] = "invalid_credentials"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except Exception as e:
                    _LOGGER.error("Unexpected error during login: %s", e)
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL, default=self._email): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
            description_placeholders={
                "support_url": "https://github.com/aiautobusinesses/rointe-hacs"
            }
        )

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    async def _async_login(self, hass: HomeAssistant, email: str, password: str) -> str:
        """Login to Rointe (Firebase) and return refresh_token."""
        if not self._is_valid_email(email):
            raise InvalidCredentials("Invalid email format")
        
        if not password or len(password) < 6:
            raise InvalidCredentials("Password too short")

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(SIGNIN_URL, json=payload) as resp:
                    if resp.status == 200:
                        try:
                            data = await resp.json()
                            if "refreshToken" not in data:
                                raise InvalidAuth("No refresh token in response")
                            
                            _LOGGER.debug("Login successful for %s", email)
                            return data["refreshToken"]
                            
                        except (ValueError, KeyError) as e:
                            _LOGGER.error("Invalid response format: %s", e)
                            raise InvalidAuth("Invalid response format")
                    
                    elif resp.status == 400:
                        try:
                            error_data = await resp.json()
                            error_message = error_data.get("error", {}).get("message", "Unknown error")
                            
                            if "INVALID_EMAIL" in error_message or "EMAIL_NOT_FOUND" in error_message:
                                raise InvalidCredentials("Email not found or invalid")
                            elif "INVALID_PASSWORD" in error_message or "WRONG_PASSWORD" in error_message:
                                raise InvalidCredentials("Invalid password")
                            elif "USER_DISABLED" in error_message:
                                raise InvalidAuth("User account has been disabled")
                            elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_message:
                                raise InvalidAuth("Too many failed attempts. Please try again later")
                            else:
                                _LOGGER.error("Authentication error: %s", error_message)
                                raise InvalidAuth(f"Authentication failed: {error_message}")
                                
                        except (ValueError, KeyError):
                            error_text = await resp.text()
                            raise InvalidAuth(f"Authentication failed: {error_text}")
                    
                    elif resp.status == 429:
                        raise InvalidAuth("Too many requests. Please try again later")
                    
                    elif resp.status >= 500:
                        raise CannotConnect("Rointe service is temporarily unavailable")
                    
                    else:
                        error_text = await resp.text()
                        _LOGGER.error("Unexpected response %d: %s", resp.status, error_text)
                        raise CannotConnect(f"Unexpected error: {resp.status}")
                        
        except aiohttp.ClientError as e:
            _LOGGER.error("Network error during login: %s", e)
            raise CannotConnect(f"Network error: {e}")
        except (InvalidCredentials, InvalidAuth, CannotConnect):
            raise
        except Exception as e:
            _LOGGER.error("Unexpected error during login: %s", e)
            raise CannotConnect(f"Unexpected error: {e}")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return RointeOptionsFlowHandler(config_entry)


class RointeOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Rointe integration."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("show_debug_logs", default=False): bool,
            }),
            description_placeholders={
                "current_email": self.config_entry.data.get("email", "Unknown")
            }
        )