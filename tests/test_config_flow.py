"""Tests for SMD D-KEYS config and reauth flows."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from custom_components.smd_d_keys.api import SmdAuthSession
from custom_components.smd_d_keys.const import (
    CONF_ACCOUNT_ID,
    CONF_OTP,
    CONF_PHONE,
    CONF_SELECTED_DOORS,
    CONF_TOKEN,
    DEFAULT_CMDC_URL,
    DEFAULT_L2_URL,
    DOMAIN,
)
from custom_components.smd_d_keys.models import SmdDoor
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOOR = SmdDoor(
    id="door-hash",
    title="Front Door",
    address="Hidden address",
    code_key="key-1",
    mqtt_topic="panel/topic-1",
    command="cmd-open",
    uid="door-1",
    code_mp="panel-1",
    room_number="1",
)


async def test_config_flow_success(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Configure an account through phone + call code."""
    with patch("custom_components.smd_d_keys.config_flow.SmdDKeysClient") as client_cls:
        client = client_cls.return_value
        client.async_request_otp = AsyncMock()
        client.async_verify_otp = AsyncMock(
            return_value=SmdAuthSession(phone="79991234567", token="token-1")
        )
        client.async_get_servers = AsyncMock(return_value={"CMDC": DEFAULT_CMDC_URL})
        client.async_get_doors = AsyncMock(return_value=[DOOR])
        client.cmdc_url = DEFAULT_CMDC_URL
        client.l2_url = DEFAULT_L2_URL

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_PHONE: "+7 999 123-45-67"},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "otp"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_OTP: "123-456"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "select_doors"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SELECTED_DOORS: ["door-hash"]}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_TOKEN] == "token-1"
    assert result["data"][CONF_ACCOUNT_ID] == "79991234567"
    assert result["options"][CONF_SELECTED_DOORS] == ["door-hash"]
    client.async_verify_otp.assert_awaited_once_with("79991234567", "123456")


async def test_config_flow_rejects_short_call_code(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Reject a call code before sending malformed input to SMD."""
    with patch("custom_components.smd_d_keys.config_flow.SmdDKeysClient") as client_cls:
        client = client_cls.return_value
        client.async_request_otp = AsyncMock()

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_PHONE: "+7 999 123-45-67"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_OTP: "12345"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "otp"
    assert result["errors"] == {CONF_OTP: "invalid_call_code"}
    client.async_verify_otp.assert_not_called()


async def test_reauth_updates_token(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Reauth keeps the existing entry and updates the token."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="SMD D-KEYS",
        unique_id="79991234567",
        data={
            CONF_ACCOUNT_ID: "79991234567",
            CONF_PHONE: "79991234567",
            CONF_TOKEN: "old-token",
        },
    )
    entry.add_to_hass(hass)

    with (
        patch("custom_components.smd_d_keys.config_flow.SmdDKeysClient") as client_cls,
        patch(
            "custom_components.smd_d_keys.api.SmdDKeysClient.async_get_servers",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "custom_components.smd_d_keys.api.SmdDKeysClient.async_get_doors",
            new=AsyncMock(return_value=[DOOR]),
        ),
        patch(
            "custom_components.smd_d_keys.api.SmdDKeysClient.async_get_cameras",
            new=AsyncMock(return_value=[]),
        ),
    ):
        client = client_cls.return_value
        client.async_request_otp = AsyncMock()
        client.async_verify_otp = AsyncMock(
            return_value=SmdAuthSession(phone="79991234567", token="new-token")
        )
        client.async_get_servers = AsyncMock(return_value={"CMDC": DEFAULT_CMDC_URL})
        client.async_get_doors = AsyncMock(return_value=[DOOR])
        client.cmdc_url = DEFAULT_CMDC_URL
        client.l2_url = DEFAULT_L2_URL

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
            data=entry.data,
        )
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PHONE: "79991234567"}
        )
        assert result["step_id"] == "reauth_otp"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_OTP: "123456"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_TOKEN] == "new-token"
