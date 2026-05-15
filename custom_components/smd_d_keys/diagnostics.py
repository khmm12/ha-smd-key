"""Diagnostics for SMD D-KEYS."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant

from . import SmdDKeysConfigEntry
from .const import (
    CONF_ACCOUNT_ID,
    CONF_CMDC_URL,
    CONF_PHONE,
    CONF_SELECTED_DOORS,
    CONF_TOKEN,
)

TO_REDACT = {
    CONF_ACCOUNT_ID,
    CONF_CMDC_URL,
    CONF_PHONE,
    CONF_SELECTED_DOORS,
    CONF_TOKEN,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SmdDKeysConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data = getattr(entry, "runtime_data", None)
    coordinator = getattr(runtime_data, "coordinator", None)
    doors = coordinator.data if coordinator else {}
    return {
        "entry": {
            "data": _redact(entry.data),
            "options": _redact(entry.options),
        },
        "runtime": {
            "door_count": len(doors or {}),
            "last_update_success": bool(
                coordinator.last_update_success if coordinator else False
            ),
        },
    }


def _redact(value: Any) -> Any:
    """Recursively redact sensitive diagnostic values."""
    if isinstance(value, Mapping):
        return {
            key: "**REDACTED**" if key in TO_REDACT else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
