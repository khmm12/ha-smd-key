"""Device registry helpers for SMD D-KEYS."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN

ACCOUNT_SUFFIX_DIGITS = 4


def account_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the account-level device for notifications and photos."""
    suffix = ""
    if entry.unique_id and len(entry.unique_id) >= ACCOUNT_SUFFIX_DIGITS:
        suffix = f" ****{entry.unique_id[-ACCOUNT_SUFFIX_DIGITS:]}"
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="SMD",
        model="D-KEYS account",
        name=f"Уведомления{suffix}",
        entry_type=DeviceEntryType.SERVICE,
    )
