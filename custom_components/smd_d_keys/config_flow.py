"""Config flow for SMD D-KEYS."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    CALL_CODE_DIGITS,
    SmdApiError,
    SmdAuthSession,
    SmdConnectionError,
    SmdDKeysClient,
    SmdInvalidOtpError,
    normalize_call_code,
    normalize_phone,
)
from .const import (
    CONF_ACCOUNT_ID,
    CONF_CMDC_URL,
    CONF_L2_URL,
    CONF_OTP,
    CONF_PHONE,
    CONF_RELOCK_DELAY,
    CONF_SELECTED_DOORS,
    CONF_TOKEN,
    DEFAULT_RELOCK_DELAY,
    DOMAIN,
)
from .models import SmdDoor

MIN_PHONE_DIGITS = 10
PHONE_TITLE_SUFFIX_DIGITS = 4

_LOGGER = logging.getLogger(__name__)


class SmdDKeysConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a SMD D-KEYS config flow."""

    VERSION = 1

    _phone: str | None = None
    _auth_session: SmdAuthSession | None = None
    _doors: list[SmdDoor]
    _client: SmdDKeysClient | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the first phone-number step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            phone = normalize_phone(user_input[CONF_PHONE])
            if len(phone) < MIN_PHONE_DIGITS:
                errors[CONF_PHONE] = "invalid_phone"
            else:
                self._phone = phone
                self._client = self._new_client(phone=phone)
                _LOGGER.debug(
                    "Starting SMD config flow authentication call: phone_digits=%s",
                    len(phone),
                )
                try:
                    await self._client.async_request_otp(phone)
                except SmdConnectionError:
                    errors["base"] = "cannot_connect"
                except SmdApiError:
                    errors["base"] = "invalid_auth"
                else:
                    _LOGGER.debug("SMD config flow authentication call requested")
                    return await self.async_step_otp()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_PHONE): str}),
            errors=errors,
        )

    async def async_step_otp(  # noqa: PLR0912
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle call-code verification and door discovery."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if self._phone is None or self._client is None:
                return await self.async_step_user()
            call_code = normalize_call_code(user_input[CONF_OTP])
            if len(call_code) != CALL_CODE_DIGITS:
                errors[CONF_OTP] = "invalid_call_code"
            else:
                try:
                    _LOGGER.debug("Verifying SMD config flow call code")
                    self._auth_session = await self._client.async_verify_otp(
                        self._phone, call_code
                    )
                except SmdInvalidOtpError:
                    errors[CONF_OTP] = "invalid_otp"
                except SmdConnectionError:
                    errors["base"] = "cannot_connect"
                except SmdApiError as err:
                    _LOGGER.warning(
                        "SMD call-code verification failed: %s", type(err).__name__
                    )
                    errors["base"] = "invalid_auth"
                else:
                    try:
                        await self._client.async_get_servers()
                        self._doors = await self._client.async_get_doors()
                    except SmdConnectionError:
                        errors["base"] = "cannot_connect"
                    except SmdApiError as err:
                        _LOGGER.warning(
                            "SMD door discovery failed after successful call-code "
                            "verification: %s",
                            type(err).__name__,
                        )
                        errors["base"] = "cannot_fetch_doors"
                    else:
                        if not self._doors:
                            errors["base"] = "no_doors"
                        else:
                            _LOGGER.debug(
                                "SMD config flow discovered doors: count=%s",
                                len(self._doors),
                            )
                            return await self.async_step_select_doors()

        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required(CONF_OTP): str}),
            errors=errors,
        )

    async def async_step_select_doors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user select which doors become lock entities."""
        errors: dict[str, str] = {}
        if self._auth_session is None or self._client is None:
            return await self.async_step_user()

        if user_input is not None:
            selected = list(user_input[CONF_SELECTED_DOORS])
            if not selected:
                errors[CONF_SELECTED_DOORS] = "no_doors_selected"
            else:
                await self.async_set_unique_id(self._auth_session.account_id)
                self._abort_if_unique_id_configured()
                _LOGGER.debug(
                    "Creating SMD config entry: selected_doors=%s",
                    len(selected),
                )
                return self.async_create_entry(
                    title=_entry_title(self._auth_session.phone),
                    data={
                        CONF_ACCOUNT_ID: self._auth_session.account_id,
                        CONF_PHONE: self._auth_session.phone,
                        CONF_TOKEN: self._auth_session.token,
                        CONF_CMDC_URL: self._client.cmdc_url,
                        CONF_L2_URL: self._client.l2_url,
                    },
                    options={
                        CONF_SELECTED_DOORS: selected,
                        CONF_RELOCK_DELAY: DEFAULT_RELOCK_DELAY,
                    },
                )

        door_ids = [door.id for door in self._doors]
        return self.async_show_form(
            step_id="select_doors",
            data_schema=_doors_schema(self._doors, selected=door_ids),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication for an existing entry."""
        self._phone = str(entry_data.get(CONF_PHONE, ""))
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Request a fresh authentication call for reauthentication."""
        errors: dict[str, str] = {}
        if user_input is not None:
            phone = normalize_phone(user_input[CONF_PHONE])
            self._phone = phone
            self._client = self._new_client(phone=phone)
            _LOGGER.debug(
                "Starting SMD reauth call request: phone_digits=%s",
                len(phone),
            )
            try:
                await self._client.async_request_otp(phone)
            except SmdConnectionError:
                errors["base"] = "cannot_connect"
            except SmdApiError:
                errors["base"] = "invalid_auth"
            else:
                _LOGGER.debug("SMD reauth call requested")
                return await self.async_step_reauth_otp()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_PHONE, default=self._phone or ""): str}
            ),
            errors=errors,
        )

    async def async_step_reauth_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Verify the reauth call code and update the existing entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if self._phone is None or self._client is None:
                return await self.async_step_reauth_confirm()
            call_code = normalize_call_code(user_input[CONF_OTP])
            if len(call_code) != CALL_CODE_DIGITS:
                errors[CONF_OTP] = "invalid_call_code"
            else:
                try:
                    _LOGGER.debug("Verifying SMD reauth call code")
                    auth_session = await self._client.async_verify_otp(
                        self._phone, call_code
                    )
                    await self._client.async_get_servers()
                    await self._client.async_get_doors()
                except SmdInvalidOtpError:
                    errors[CONF_OTP] = "invalid_otp"
                except SmdConnectionError:
                    errors["base"] = "cannot_connect"
                except SmdApiError as err:
                    _LOGGER.warning(
                        "SMD reauthentication failed: %s", type(err).__name__
                    )
                    errors["base"] = "invalid_auth"
                else:
                    entry = self._get_reauth_entry()
                    _LOGGER.debug("Updating SMD config entry after successful reauth")
                    return self.async_update_reload_and_abort(
                        entry,
                        unique_id=auth_session.account_id,
                        data={
                            **entry.data,
                            CONF_ACCOUNT_ID: auth_session.account_id,
                            CONF_PHONE: auth_session.phone,
                            CONF_TOKEN: auth_session.token,
                            CONF_CMDC_URL: self._client.cmdc_url,
                            CONF_L2_URL: self._client.l2_url,
                        },
                    )

        return self.async_show_form(
            step_id="reauth_otp",
            data_schema=vol.Schema({vol.Required(CONF_OTP): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SmdDKeysOptionsFlow:
        """Return the options flow."""
        return SmdDKeysOptionsFlow(config_entry)

    def _new_client(self, *, phone: str, token: str = "") -> SmdDKeysClient:
        """Create a config-flow API client."""
        return SmdDKeysClient(
            async_get_clientsession(self.hass),
            phone=phone,
            token=token,
        )


class SmdDKeysOptionsFlow(config_entries.OptionsFlow):
    """Handle SMD D-KEYS options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage selected doors and relock delay."""
        errors: dict[str, str] = {}
        doors: list[SmdDoor] = []
        client = SmdDKeysClient(
            async_get_clientsession(self.hass),
            phone=self._entry.data[CONF_PHONE],
            token=self._entry.data[CONF_TOKEN],
            cmdc_url=self._entry.data.get(CONF_CMDC_URL),
            l2_url=self._entry.data.get(CONF_L2_URL),
        )
        try:
            await client.async_get_servers()
            doors = await client.async_get_doors()
        except SmdConnectionError:
            errors["base"] = "cannot_connect"
        except SmdApiError:
            errors["base"] = "invalid_auth"

        if user_input is not None and not errors:
            selected = list(user_input[CONF_SELECTED_DOORS])
            if not selected:
                errors[CONF_SELECTED_DOORS] = "no_doors_selected"
            else:
                _LOGGER.debug(
                    "Updating SMD options: selected_doors=%s relock_delay=%s",
                    len(selected),
                    user_input[CONF_RELOCK_DELAY],
                )
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SELECTED_DOORS: selected,
                        CONF_RELOCK_DELAY: user_input[CONF_RELOCK_DELAY],
                    },
                )

        selected = list(
            self._entry.options.get(
                CONF_SELECTED_DOORS,
                [door.id for door in doors],
            )
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_doors_schema(
                doors,
                selected=selected,
                relock_delay=self._entry.options.get(
                    CONF_RELOCK_DELAY, DEFAULT_RELOCK_DELAY
                ),
            ),
            errors=errors,
        )


def _doors_schema(
    doors: list[SmdDoor],
    *,
    selected: list[str],
    relock_delay: int | None = None,
) -> vol.Schema:
    """Build a door-selection schema."""
    schema: dict[Any, Any] = {
        vol.Required(CONF_SELECTED_DOORS, default=selected): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=door.id, label=door.display_name)
                    for door in doors
                ],
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        )
    }
    if relock_delay is not None:
        schema[vol.Required(CONF_RELOCK_DELAY, default=relock_delay)] = vol.All(
            vol.Coerce(int), vol.Range(min=1, max=120)
        )
    return vol.Schema(schema)


def _entry_title(phone: str) -> str:
    """Return a redacted config entry title."""
    if len(phone) < PHONE_TITLE_SUFFIX_DIGITS:
        return "SMD D-KEYS"
    return f"SMD D-KEYS ****{phone[-PHONE_TITLE_SUFFIX_DIGITS:]}"
