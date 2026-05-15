"""Tests for SMD D-KEYS diagnostics."""

from __future__ import annotations

from custom_components.smd_d_keys.const import (
    CONF_ACCOUNT_ID,
    CONF_PHONE,
    CONF_SELECTED_DOORS,
    CONF_TOKEN,
    DOMAIN,
)
from custom_components.smd_d_keys.diagnostics import async_get_config_entry_diagnostics
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_diagnostics_redacts_sensitive_data(hass: HomeAssistant) -> None:
    """Diagnostics must not expose credentials or personal identifiers."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ACCOUNT_ID: "79991234567",
            CONF_PHONE: "79991234567",
            CONF_TOKEN: "token",
        },
        options={CONF_SELECTED_DOORS: ["door-hash"]},
    )
    entry.add_to_hass(hass)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["data"][CONF_TOKEN] == "**REDACTED**"
    assert diagnostics["entry"]["data"][CONF_PHONE] == "**REDACTED**"
    assert diagnostics["entry"]["data"][CONF_ACCOUNT_ID] == "**REDACTED**"
    assert diagnostics["entry"]["options"][CONF_SELECTED_DOORS] == "**REDACTED**"
