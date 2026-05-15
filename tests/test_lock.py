"""Tests for SMD D-KEYS lock entities."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from custom_components.smd_d_keys.const import (
    CONF_ACCOUNT_ID,
    CONF_PHONE,
    CONF_RELOCK_DELAY,
    CONF_SELECTED_DOORS,
    CONF_TOKEN,
    DOMAIN,
)
from custom_components.smd_d_keys.models import SmdDoor
from homeassistant.components.lock import LockState
from homeassistant.const import (
    SERVICE_LOCK,
    SERVICE_UNLOCK,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

DOOR = SmdDoor(
    id="door-hash",
    title="Front Door",
    address=None,
    code_key="key-1",
    mqtt_topic="panel/topic-1",
    command="cmd-open",
    uid="door-1",
    code_mp="panel-1",
    room_number="1",
)


async def test_lock_unlock_and_assumed_relock(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Unlock sends openDoor and returns to locked after the delay."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="SMD D-KEYS",
        data={
            CONF_ACCOUNT_ID: "79991234567",
            CONF_PHONE: "79991234567",
            CONF_TOKEN: "token",
        },
        options={
            CONF_SELECTED_DOORS: ["door-hash"],
            CONF_RELOCK_DELAY: 5,
        },
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.smd_d_keys.api.SmdDKeysClient.async_get_servers",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "custom_components.smd_d_keys.api.SmdDKeysClient.async_get_doors",
            new=AsyncMock(return_value=[DOOR]),
        ),
        patch(
            "custom_components.smd_d_keys.api.SmdDKeysClient.async_open_door",
            new=AsyncMock(),
        ) as open_door,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        states = hass.states.async_all("lock")
        assert len(states) == 1
        entity_id = states[0].entity_id
        assert entity_id == "lock.front_door"
        registry_entry = er.async_get(hass).async_get(entity_id)
        assert registry_entry is not None
        assert registry_entry.translation_key == "lock"
        assert hass.states.get(entity_id).state == LockState.LOCKED

        await hass.services.async_call(
            "lock",
            SERVICE_UNLOCK,
            {"entity_id": entity_id},
            blocking=True,
        )
        assert hass.states.get(entity_id).state == LockState.UNLOCKED
        open_door.assert_awaited_once()

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == LockState.LOCKED

        await hass.services.async_call(
            "lock",
            SERVICE_LOCK,
            {"entity_id": entity_id},
            blocking=True,
        )
        assert hass.states.get(entity_id).state == LockState.LOCKED
