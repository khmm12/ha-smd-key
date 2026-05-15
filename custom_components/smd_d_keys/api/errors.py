"""Errors and auth models for the SMD D-KEYS API."""

from __future__ import annotations

from dataclasses import dataclass


class SmdError(Exception):
    """Base error for SMD D-KEYS."""


class SmdConnectionError(SmdError):
    """Raised when SMD cannot be reached."""


class SmdApiError(SmdError):
    """Raised when SMD returns an application-level error."""


class SmdAuthError(SmdApiError):
    """Raised when SMD authentication is invalid or expired."""


class SmdInvalidOtpError(SmdAuthError):
    """Raised when SMD rejects the call-code value sent as `otp`."""


class SmdRateLimitError(SmdApiError):
    """Raised when SMD rate-limits a request."""


class SmdMalformedResponseError(SmdApiError):
    """Raised when SMD returns an unexpected payload."""


@dataclass(frozen=True, slots=True)
class SmdAuthSession:
    """Authenticated SMD session."""

    phone: str
    token: str

    @property
    def account_id(self) -> str:
        """Return the stable account identifier available in the app flow."""
        return self.phone
