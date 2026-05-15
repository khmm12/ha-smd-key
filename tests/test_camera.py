"""Tests for SMD D-KEYS camera entities."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from custom_components.smd_d_keys.api import SmdConnectionError
from custom_components.smd_d_keys.camera import SmdDKeysCamera
from custom_components.smd_d_keys.const import (
    CONF_ACCOUNT_ID,
    CONF_PHONE,
    CONF_SELECTED_DOORS,
    CONF_TOKEN,
    DOMAIN,
)
from custom_components.smd_d_keys.models import SmdCamera, SmdDoor
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
    options=("videoTranslate",),
)

CAMERA = SmdCamera(
    id="camera-hash",
    door_id="door-hash",
    title="Front Door",
    address=None,
    code_key="key-1",
    code_mp="panel-1",
    srv="L3",
    protocol="RTSP",
    uid="camera-1",
    online=True,
)

UNMATCHED_CAMERA = SmdCamera(
    id="camera-only-hash",
    door_id="camera-only-hash",
    title="Standalone camera",
    address=None,
    code_key="camera-key-1",
    code_mp="camera-panel-1",
    srv="L3",
    protocol="RTSP",
    uid="camera-2",
    online=True,
)


async def test_camera_entity_setup(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Set up a camera entity for a video-capable selected door."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="SMD D-KEYS",
        data={
            CONF_ACCOUNT_ID: "79991234567",
            CONF_PHONE: "79991234567",
            CONF_TOKEN: "token",
        },
        options={CONF_SELECTED_DOORS: ["door-hash"]},
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
            "custom_components.smd_d_keys.api.SmdDKeysClient.async_get_cameras",
            new=AsyncMock(return_value=[CAMERA]),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    states = hass.states.async_all("camera")
    assert len(states) == 1
    assert states[0].attributes["friendly_name"] == "Front Door Camera"

    entity_registry = er.async_get(hass)
    camera_entry = entity_registry.async_get(states[0].entity_id)
    door_device = dr.async_get(hass).async_get_device({(DOMAIN, "door-hash")})
    assert door_device is not None
    assert camera_entry is not None
    assert camera_entry.device_id == door_device.id
    assert camera_entry.translation_key == "camera"


async def test_unmatched_camera_entity_setup_when_doors_selected(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Set up account-level cameras that are not linked to selected doors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="SMD D-KEYS",
        data={
            CONF_ACCOUNT_ID: "79991234567",
            CONF_PHONE: "79991234567",
            CONF_TOKEN: "token",
        },
        options={CONF_SELECTED_DOORS: ["door-hash"]},
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
            "custom_components.smd_d_keys.api.SmdDKeysClient.async_get_cameras",
            new=AsyncMock(return_value=[UNMATCHED_CAMERA]),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    states = hass.states.async_all("camera")
    assert len(states) == 1
    assert states[0].attributes["friendly_name"] == "Standalone camera Camera"


async def test_camera_stream_source(hass: HomeAssistant) -> None:
    """Return the RTSP stream source from the client."""
    client = SimpleNamespace(
        async_get_camera_stream_source=AsyncMock(
            return_value="rtsp://user:pass@example/live"
        )
    )
    coordinator = SimpleNamespace(
        client=client,
        data={"door-hash": DOOR},
        last_update_success=True,
        config_entry=SimpleNamespace(async_start_reauth=lambda hass: None),
    )
    entity = SmdDKeysCamera(coordinator, CAMERA)
    entity.hass = hass

    assert await entity.stream_source() == "rtsp://user:pass@example/live"
    client.async_get_camera_stream_source.assert_awaited_once_with(CAMERA)


async def test_camera_stream_source_returns_none_on_connection_error(
    hass: HomeAssistant,
) -> None:
    """Do not fail entity setup when HA probes the stream during a network blip."""
    client = SimpleNamespace(
        async_get_camera_stream_source=AsyncMock(
            side_effect=SmdConnectionError("Failed to connect to SMD")
        )
    )
    coordinator = SimpleNamespace(
        client=client,
        data={"door-hash": DOOR},
        last_update_success=True,
        config_entry=SimpleNamespace(async_start_reauth=lambda hass: None),
    )
    entity = SmdDKeysCamera(coordinator, CAMERA)
    entity.hass = hass

    assert await entity.stream_source() is None


async def test_camera_snapshot_returns_none(hass: HomeAssistant) -> None:
    """Avoid the base camera class still-image NotImplementedError."""
    coordinator = SimpleNamespace(
        client=SimpleNamespace(),
        data={"door-hash": DOOR},
        last_update_success=True,
        config_entry=SimpleNamespace(async_start_reauth=lambda hass: None),
    )
    entity = SmdDKeysCamera(coordinator, CAMERA)
    entity.hass = hass

    assert entity.use_stream_for_stills is True
    assert await entity.async_camera_image() is None
