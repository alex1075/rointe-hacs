"""
Rointe Configuration Flow

Handles configuration flow for the dual authentication system.
Validates credentials using REST API authentication.
"""

import logging
import voluptuous as vol
import re
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .auth import RointeAuth, RointeRestAuthError, RointeFirebaseAuthError

_LOGGER = logging.getLogger(__name__)

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
                    
                    # Validate credentials using dual authentication system
                    await self._async_validate_credentials(email, password)
                    
                    return self.async_create_entry(
                        title=f"Rointe Nexa ({email})",
                        data={
                            "email": email,
                            "password": password
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

    async def _async_validate_credentials(self, email: str, password: str) -> None:
        """Validate credentials using the dual authentication system."""
        if not self._is_valid_email(email):
            raise InvalidCredentials("Invalid email format")
        
        if not password or len(password) < 6:
            raise InvalidCredentials("Password too short")

        _LOGGER.debug("Validating credentials for email: %s", email)
        
        try:
            # Create auth instance and validate credentials
            auth = RointeAuth(email, password)
            async with auth:
                # Test REST API authentication
                if not await auth.async_validate_credentials():
                    raise InvalidAuth("Invalid email or password")
                
                _LOGGER.debug("Credentials validation successful for %s", email)
                
        except RointeRestAuthError as e:
            _LOGGER.error("REST authentication failed: %s", e)
            if "Invalid credentials" in str(e) or "INVALID_LOGIN_CREDENTIALS" in str(e):
                raise InvalidCredentials("Invalid email or password")
            elif "USER_DISABLED" in str(e):
                raise InvalidAuth("User account has been disabled")
            elif "TOO_MANY_ATTEMPTS" in str(e):
                raise InvalidAuth("Too many failed attempts. Please try again later")
            else:
                raise InvalidAuth(f"Authentication failed: {e}")
                
        except RointeFirebaseAuthError as e:
            _LOGGER.error("Firebase authentication failed: %s", e)
            # Firebase auth failure is not critical for validation
            # We only need REST auth to work for credential validation
            _LOGGER.warning("Firebase authentication failed, but REST auth succeeded")
            
        except Exception as e:
            _LOGGER.error("Unexpected error during credential validation: %s", e)
            if "Network" in str(e) or "timeout" in str(e).lower():
                raise CannotConnect(f"Network error: {e}")
            else:
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