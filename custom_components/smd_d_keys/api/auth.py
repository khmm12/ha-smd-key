"""Authentication actions for the SMD D-KEYS API."""

from __future__ import annotations

import logging

from . import helpers
from .base import SmdBaseClient
from .errors import SmdAuthSession, SmdInvalidOtpError, SmdMalformedResponseError

_LOGGER = logging.getLogger(__name__)


class SmdAuthActions(SmdBaseClient):
    """Phone call-code authentication flow used by the mobile app."""

    async def async_request_otp(self, phone: str) -> None:
        """Request an authentication call for a normalized phone number."""
        _LOGGER.debug("Requesting SMD authentication call")
        payload = await self._post_mde_form(
            self._common_params({"action": "regPhone"}, mobile=phone)
        )
        self._raise_for_error(payload, authenticated=False)
        _LOGGER.debug("SMD authentication call request accepted")

    async def async_verify_otp(self, phone: str, otp: str) -> SmdAuthSession:
        """Exchange phone + call code for a session token."""
        call_code = helpers.normalize_call_code(otp)
        payload = await self._post_mde_form(
            self._common_params(
                {
                    "action": "sendPin",
                    "otp": call_code,
                },
                mobile=phone,
            )
        )
        self._raise_for_error(payload, authenticated=False, otp=True)
        try:
            data = helpers.expect_mapping(payload.get("DATA"), "DATA")
            token = helpers.expect_text(data.get("Token"), "DATA.Token")
            response_phone = helpers.expect_text(
                data.get("PhoneNumber") or phone, "DATA.PhoneNumber"
            )
        except SmdMalformedResponseError as err:
            _LOGGER.warning(
                "SMD sendPin response did not include the expected token: %s",
                helpers.safe_payload_summary(payload),
            )
            raise SmdInvalidOtpError(
                "SMD did not return a token for this call code"
            ) from err
        self.phone = response_phone
        self.token = token
        _LOGGER.debug("SMD call-code verification accepted")
        return SmdAuthSession(phone=response_phone, token=token)
