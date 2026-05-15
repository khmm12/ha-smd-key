"""Tests for the SMD D-KEYS API client."""

from __future__ import annotations

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses
from custom_components.smd_d_keys.api import (
    SmdDKeysClient,
    normalize_call_code,
    normalize_phone,
)
from custom_components.smd_d_keys.const import (
    DEFAULT_CMDC_URL,
    DEFAULT_L2_URL,
    DEFAULT_MDE_URL,
)
from custom_components.smd_d_keys.models import SmdDoor
from yarl import URL


@pytest.mark.asyncio
async def test_phone_otp_key_and_open_flow() -> None:
    """Exercise the reverse-engineered MVP API calls."""
    with aioresponses() as mocked:
        mocked.post(DEFAULT_MDE_URL, payload={"error": False, "critical": ""})
        mocked.post(
            DEFAULT_MDE_URL,
            payload={
                "error": False,
                "critical": "",
                "DATA": {"PhoneNumber": "79991234567", "Token": "token-1"},
            },
        )
        mocked.post(
            DEFAULT_MDE_URL,
            payload={
                "error": False,
                "critical": "",
                "DATA": [{"server": "CMDC", "domen": DEFAULT_CMDC_URL}],
            },
        )
        mocked.post(
            DEFAULT_MDE_URL,
            payload={
                "error": False,
                "critical": "",
                "DATA": [
                    {
                        "Nickname": "Front Door",
                        "Address": "Hidden address",
                        "mqtt": "panel/topic-1",
                        "text": "cmd-open",
                        "uid": "door-1",
                        "codeMP": "panel-1",
                        "roomNumber": "1",
                    }
                ],
            },
        )
        mocked.post(
            f"{DEFAULT_CMDC_URL}/openDoor",
            payload={"error": False, "DATA": "ok"},
        )

        async with ClientSession() as session:
            client = SmdDKeysClient(session)
            phone = normalize_phone("+7 (999) 123-45-67")
            await client.async_request_otp(phone)
            auth = await client.async_verify_otp(phone, "123456")
            await client.async_get_servers()
            doors = await client.async_get_doors()
            await client.async_open_door(doors[0])

    assert auth.token == "token-1"
    assert doors[0].title == "Front Door"
    assert doors[0].mqtt_topic == "panel/topic-1"
    calls = mocked.requests[("POST", URL(f"{DEFAULT_CMDC_URL}/openDoor"))]
    assert calls[0].kwargs["json"]["topic"] == "panel/topic-1"
    assert calls[0].kwargs["json"]["command"] == "cmd-open"
    assert calls[0].kwargs["json"]["uid"] == "topic-1"


def test_normalize_phone() -> None:
    """Normalize common Russian phone input."""
    assert normalize_phone("+7 (999) 123-45-67") == "79991234567"
    assert normalize_phone("8 999 123-45-67") == "79991234567"


def test_normalize_call_code() -> None:
    """Normalize formatted caller-number digits to the API call code."""
    assert normalize_call_code("12-34 56") == "123456"


@pytest.mark.asyncio
async def test_mqtt_option_lookup_for_key_without_inline_topic() -> None:
    """Fetch MQTT option data when getKey omits the open topic."""
    with aioresponses() as mocked:
        mocked.post(
            DEFAULT_MDE_URL,
            payload={
                "error": False,
                "critical": "",
                "DATA": [
                    {"server": "L2", "domen": DEFAULT_L2_URL},
                    {"server": "cmdc", "domen": DEFAULT_CMDC_URL},
                ],
            },
        )
        mocked.post(
            DEFAULT_MDE_URL,
            payload={
                "error": False,
                "critical": "",
                "DATA": [
                    {
                        "codeKey": "1129",
                        "Nickname": "Front Door",
                        "Address": "Hidden address",
                        "codeMP": "panel-1",
                        "options_exist": ["mqtt"],
                    }
                ],
            },
        )
        mocked.post(
            DEFAULT_MDE_URL,
            payload={
                "error": False,
                "critical": "",
                "DATA": {
                    "mqtt": {
                        "topicCommand": "smddev2/panel-topic-1",
                        "openCommand": "cmd1",
                    }
                },
            },
        )
        mocked.post(
            f"{DEFAULT_CMDC_URL}/openDoor",
            payload={"error": "false", "DATA": "ok"},
        )

        async with ClientSession() as session:
            client = SmdDKeysClient(session, phone="79991234567", token="token-1")
            await client.async_get_servers()
            doors = await client.async_get_doors()
            await client.async_open_door(doors[0])

    assert doors[0].mqtt_topic == "smddev2/panel-topic-1"
    assert doors[0].command == "cmd1"
    assert doors[0].code_mp == "panel-1"
    option_calls = mocked.requests[("POST", URL(DEFAULT_MDE_URL))]
    assert option_calls[2].kwargs["data"]["action"] == "getDataOption"
    assert option_calls[2].kwargs["data"]["option"] == "mqtt"
    assert option_calls[2].kwargs["data"]["codeKey"] == "1129"
    calls = mocked.requests[("POST", URL(f"{DEFAULT_CMDC_URL}/openDoor"))]
    assert calls[0].kwargs["json"]["topic"] == "smddev2/panel-topic-1"
    assert calls[0].kwargs["json"]["command"] == "cmd1"
    assert calls[0].kwargs["json"]["uid"] == "panel-topic-1"


@pytest.mark.asyncio
async def test_camera_list_and_rtsp_stream_source() -> None:
    """Fetch camera broadcasts and build the RTSP stream source."""
    door = SmdDoor(
        id="door-hash",
        title="Front Door",
        address="Hidden address",
        code_key="1129",
        mqtt_topic="smddev2/panel-topic-1",
        command="cmd1",
        uid="door-1",
        code_mp="panel-1",
        room_number="1",
        options=("videoTranslate",),
    )
    with aioresponses() as mocked:
        mocked.post(
            DEFAULT_MDE_URL,
            payload={
                "error": False,
                "critical": "",
                "DATA": [
                    {"server": "L3", "domen": "http://stale-l3.example"},
                    {"server": "l3", "domen": "https://video-l3.example"},
                ],
            },
        )
        mocked.post(
            DEFAULT_MDE_URL,
            payload={
                "error": False,
                "critical": "",
                "DATA": [
                    {
                        "codeKey": "1129",
                        "Nickname": "Entrance camera",
                        "Address": "Hidden address",
                        "codeMP": "panel-1",
                        "protocol": "RTSP",
                        "srv": "L3",
                        "UID": "camera-1",
                        "Online": 1,
                    }
                ],
            },
        )
        mocked.post(
            "https://video-l3.example/app/getVideoBroadcastByProtocol",
            payload={
                "error": False,
                "DATA": {
                    "login": "user@example",
                    "password": "pa ss",
                    "protocol": "RTSP",
                    "url": "camera.example/live",
                },
            },
        )

        async with ClientSession() as session:
            client = SmdDKeysClient(session, phone="79991234567", token="token-1")
            await client.async_get_servers()
            cameras = await client.async_get_cameras({"door-hash": door})
            camera = cameras[0]
            stream_source = await client.async_get_camera_stream_source(camera)

    assert len(cameras) == 1
    assert camera.door_id == "door-hash"
    assert camera.title == "Entrance camera"
    assert camera.code_key == "1129"
    assert camera.code_mp == "panel-1"
    assert camera.srv == "L3"
    assert camera.online is True
    assert stream_source == "rtsp://user%40example:pa%20ss@camera.example/live"
    calls = mocked.requests[
        ("POST", URL("https://video-l3.example/app/getVideoBroadcastByProtocol"))
    ]
    assert calls[0].kwargs["json"]["codeMP"] == "panel-1"
    assert calls[0].kwargs["json"]["protocol"] == "RTSP"


@pytest.mark.asyncio
async def test_camera_matches_door_by_code_mp_when_code_key_differs() -> None:
    """Match account-level broadcasts back to a door by panel code."""
    door = SmdDoor(
        id="door-hash",
        title="Front Door",
        address="Hidden address",
        code_key="door-code-key",
        mqtt_topic="smddev2/panel-topic-1",
        command="cmd1",
        uid="door-1",
        code_mp="panel-1",
        room_number="1",
    )
    with aioresponses() as mocked:
        mocked.post(
            DEFAULT_MDE_URL,
            payload={
                "error": False,
                "critical": "",
                "DATA": [
                    {
                        "codeKey": "broadcast-code-key",
                        "Nickname": "Entrance camera",
                        "Address": "Hidden address",
                        "codeMP": "panel-1",
                        "protocol": "RTSP",
                        "srv": "L3",
                    }
                ],
            },
        )

        async with ClientSession() as session:
            client = SmdDKeysClient(session, phone="79991234567", token="token-1")
            cameras = await client.async_get_cameras({"door-hash": door})

    assert len(cameras) == 1
    assert cameras[0].door_id == "door-hash"


@pytest.mark.asyncio
async def test_camera_metadata_absent_returns_none() -> None:
    """Treat SMD's empty getNewVideo item as no live camera."""
    door = SmdDoor(
        id="door-hash",
        title="Front Door",
        address="Hidden address",
        code_key="1129",
        mqtt_topic="smddev2/panel-topic-1",
        command="cmd1",
        uid="door-1",
        code_mp="panel-1",
        room_number="1",
        options=("videoTranslate",),
    )
    with aioresponses() as mocked:
        mocked.post(
            DEFAULT_MDE_URL,
            payload={
                "error": False,
                "critical": "10",
                "warning": "Warning #3.28.2 no cameras",
                "DATA": [
                    {
                        "codeKey": "",
                        "Nickname": "",
                        "Address": "",
                        "codeMP": "",
                        "protocol": "",
                        "srv": "",
                    }
                ],
            },
        )

        async with ClientSession() as session:
            client = SmdDKeysClient(session, phone="79991234567", token="token-1")
            camera = await client.async_get_camera_for_door(door)

    assert camera is None
