"""Shared transport for the reverse-engineered SMD D-KEYS API."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout

from ..const import (
    APP_LANG,
    APP_OS,
    APP_VERSION,
    APP_VERSION_OS,
    DEFAULT_CMDC_URL,
    DEFAULT_L2_URL,
    DEFAULT_MDE_URL,
)
from . import helpers
from .errors import (
    SmdApiError,
    SmdAuthError,
    SmdConnectionError,
    SmdInvalidOtpError,
    SmdMalformedResponseError,
    SmdRateLimitError,
)
from .helpers import JsonObject

REQUEST_TIMEOUT = ClientTimeout(total=15)
HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_RATE_LIMITED = 429
HTTP_UNAUTHORIZED = 401

_LOGGER = logging.getLogger(__name__)


class SmdBaseClient:
    """Base client with request envelope, transport, and error mapping."""

    def __init__(
        self,
        session: ClientSession,
        *,
        phone: str = "",
        token: str = "",
        mde_url: str = DEFAULT_MDE_URL,
        cmdc_url: str | None = None,
        l2_url: str | None = None,
        app_version: str = APP_VERSION,
        app_lang: str = APP_LANG,
        app_os: str = APP_OS,
        app_version_os: str = APP_VERSION_OS,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self.phone = phone
        self.token = token
        self._mde_url = mde_url
        self.cmdc_url = (cmdc_url or DEFAULT_CMDC_URL).rstrip("/")
        self.l2_url = (l2_url or DEFAULT_L2_URL).rstrip("/")
        self._app_version = app_version
        self._app_lang = app_lang
        self._app_os = app_os
        self._app_version_os = app_version_os
        self._server_urls: dict[str, str] = {}

    def _common_params(
        self, params: Mapping[str, str], *, mobile: str | None = None
    ) -> dict[str, str]:
        """Build the common app request envelope."""
        return {
            **params,
            "os": self._app_os,
            "lang": self._app_lang,
            "version": self._app_version,
            "token": self.token,
            "mobile": mobile if mobile is not None else self.phone,
            "versionOS": self._app_version_os,
        }

    async def _post_mde_form(self, data: Mapping[str, str]) -> JsonObject:
        """POST a form-encoded request to the MDE endpoint."""
        return await self._request_json("POST", self._mde_url, data=data)

    async def _post_json(self, url: str, data: Mapping[str, str]) -> JsonObject:
        """POST a JSON request to a dynamic endpoint."""
        return await self._request_json("POST", url, json=data)

    async def _request_json(self, method: str, url: str, **kwargs: Any) -> JsonObject:
        """Send a request and parse a JSON object response."""
        action = helpers.request_action(kwargs)
        _LOGGER.debug(
            "Sending SMD request: action=%s method=%s endpoint=%s",
            action,
            method,
            helpers.safe_url_summary(url),
        )
        try:
            async with self._session.request(
                method,
                url,
                timeout=REQUEST_TIMEOUT,
                **kwargs,
            ) as response:
                self._raise_for_status(response, action)
                payload = await response.json(content_type=None)
                status = response.status
        except TimeoutError as err:
            raise SmdConnectionError("Timed out connecting to SMD") from err
        except ClientError as err:
            raise SmdConnectionError("Failed to connect to SMD") from err
        except ValueError as err:
            raise SmdMalformedResponseError("SMD returned invalid JSON") from err

        if not isinstance(payload, dict):
            raise SmdMalformedResponseError("SMD returned a non-object JSON response")
        _LOGGER.debug(
            "SMD response received: action=%s status=%s data=%s",
            action,
            status,
            helpers.safe_payload_summary(payload).get("DATA"),
        )
        return payload

    @staticmethod
    def _raise_for_status(response: ClientResponse, action: str | None = None) -> None:
        """Map HTTP errors to integration errors."""
        if response.status in (HTTP_UNAUTHORIZED, HTTP_FORBIDDEN):
            _LOGGER.warning(
                "SMD request was rejected by HTTP status: action=%s status=%s",
                action,
                response.status,
            )
            raise SmdAuthError("SMD rejected the current token")
        if response.status == HTTP_RATE_LIMITED:
            raise SmdRateLimitError("SMD rate limit exceeded")
        if response.status >= HTTP_INTERNAL_SERVER_ERROR:
            raise SmdConnectionError(f"SMD server error: {response.status}")
        if response.status >= HTTP_BAD_REQUEST:
            raise SmdApiError(f"SMD request failed: {response.status}")

    @staticmethod
    def _raise_for_error(
        payload: Mapping[str, Any], *, authenticated: bool, otp: bool = False
    ) -> None:
        """Raise for an SMD `error` response."""
        if not helpers.is_error(payload.get("error")):
            return
        message = str(payload.get("message") or "SMD request failed")
        _LOGGER.warning(
            "SMD API error response: %s", helpers.safe_payload_summary(payload)
        )
        if otp:
            raise SmdInvalidOtpError("SMD rejected the call code")
        if authenticated and helpers.looks_like_auth_error(message):
            raise SmdAuthError("SMD rejected the current token")
        raise SmdApiError("SMD API request failed")
