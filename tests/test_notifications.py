"""Tests for SMD notification parsing and guest photo downloads."""

from __future__ import annotations

import json
from dataclasses import asdict

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses
from custom_components.smd_d_keys.api import SmdApiError, SmdDKeysClient
from custom_components.smd_d_keys.const import (
    DEFAULT_PUSH_URL,
    EVENT_GUEST_PHOTO,
    EVENT_INCOMING_CALL,
)
from custom_components.smd_d_keys.models import SmdDoor, SmdNotification
from custom_components.smd_d_keys.notification_coordinator import (
    filter_new_notifications,
    merge_notifications,
    normalize_last_notification_id,
)

PHOTO_URL = "https://fimg.example.test/photo/1"


def _door() -> SmdDoor:
    return SmdDoor(
        id="door-1",
        title="Front door",
        address=None,
        code_key=None,
        mqtt_topic=None,
        command=None,
        uid=None,
        code_mp="mp-1",
        room_number=None,
    )


def _unread_payload() -> dict:
    call_text = json.dumps(
        {
            "action": "receiveCall",
            "title": "Incoming call",
            "caller": "Alice",
            "fsCaller": "Alice",
            "fsPass": "secret-pass",
            "vsLogin": "secret-login",
            "codeMP": "mp-1",
            "dateTime": '"2026-01-01 10:00:00"',
        }
    )
    photo_text = json.dumps(
        {
            "title": "Guest",
            "body": "At the door",
            "file": json.dumps(
                {
                    "typeFile": "Image",
                    "url": PHOTO_URL,
                    "hash": "photo-hash",
                }
            ),
        }
    )
    return {
        "error": False,
        "message": "",
        "DATA": {
            "list": [
                {
                    "ID": 11,
                    "statusPUSH": 1,
                    "createDateTime": "2026-01-01 10:01:00",
                    "textPUSH": photo_text,
                },
                {
                    "ID": 10,
                    "statusPUSH": 1,
                    "createDateTime": "2026-01-01 10:00:00",
                    "textPUSH": call_text,
                },
            ]
        },
    }


@pytest.mark.asyncio
async def test_unread_notifications_are_parsed_and_ordered() -> None:
    """Parse call and photo notifications without exposing credentials."""
    with aioresponses() as mocked:
        mocked.post(
            f"{DEFAULT_PUSH_URL}/notification/getUnread", payload=_unread_payload()
        )

        async with ClientSession() as session:
            client = SmdDKeysClient(session)
            notifications = await client.async_get_unread_notifications(
                {"door-1": _door()}
            )

    assert [item.id for item in notifications] == [10, 11]
    call, photo = notifications
    assert call.kind == EVENT_INCOMING_CALL
    assert call.caller == "Alice"
    assert call.door_id == "door-1"
    assert call.created_at == "2026-01-01 10:00:00"
    assert photo.kind == EVENT_GUEST_PHOTO
    assert photo.body == "At the door"
    assert photo.file_url == PHOTO_URL
    serialized = json.dumps([asdict(item) for item in notifications])
    assert "secret" not in serialized


@pytest.mark.asyncio
async def test_guest_photo_download() -> None:
    """Download an image from the signed HTTPS URL."""
    notification = SmdNotification(
        id=1,
        kind=EVENT_GUEST_PHOTO,
        created_at=None,
        title=None,
        body=None,
        file_url=PHOTO_URL,
    )
    with aioresponses() as mocked:
        mocked.get(PHOTO_URL, body=b"\xff\xd8image", content_type="image/jpeg")

        async with ClientSession() as session:
            client = SmdDKeysClient(session)
            image = await client.async_get_notification_image(notification)

    assert image == b"\xff\xd8image"


@pytest.mark.asyncio
async def test_guest_photo_http_url_is_ignored() -> None:
    """Never download a signed photo URL over plaintext HTTP."""
    notification = SmdNotification(
        id=1,
        kind=EVENT_GUEST_PHOTO,
        created_at=None,
        title=None,
        body=None,
        file_url="http://fimg.example.test/photo/1",
    )
    async with ClientSession() as session:
        client = SmdDKeysClient(session)
        image = await client.async_get_notification_image(notification)

    assert image is None


@pytest.mark.asyncio
async def test_expired_guest_photo_raises_api_error() -> None:
    """Surface an expired photo link as an SMD API error."""
    notification = SmdNotification(
        id=1,
        kind=EVENT_GUEST_PHOTO,
        created_at=None,
        title=None,
        body=None,
        file_url=PHOTO_URL,
    )
    with aioresponses() as mocked:
        mocked.get(
            PHOTO_URL,
            payload={"error": True, "message": "link expired"},
            content_type="application/json",
        )

        async with ClientSession() as session:
            client = SmdDKeysClient(session)
            with pytest.raises(SmdApiError):
                await client.async_get_notification_image(notification)


def test_filter_new_notifications() -> None:
    """Emit only IDs above the stored cursor."""
    notifications = [
        SmdNotification(
            id=item_id,
            kind=EVENT_INCOMING_CALL,
            created_at=None,
            title=None,
            body=None,
        )
        for item_id in (5, 7)
    ]

    assert filter_new_notifications(notifications, None) == ([], 7)
    assert filter_new_notifications(notifications, 5) == ([notifications[1]], 7)
    assert filter_new_notifications(notifications, 7) == ([], 7)


def test_normalize_last_notification_id() -> None:
    """Treat a stored zero as an uninitialized cursor."""
    assert normalize_last_notification_id(None) is None
    assert normalize_last_notification_id(0) is None
    notification_id = 42
    assert normalize_last_notification_id(notification_id) == notification_id


def test_merge_notifications_prefers_unread() -> None:
    """Merge history with unread data and keep IDs unique."""
    history = [
        SmdNotification(
            id=1,
            kind=EVENT_INCOMING_CALL,
            created_at=None,
            title="history",
            body=None,
        ),
        SmdNotification(
            id=2,
            kind=EVENT_GUEST_PHOTO,
            created_at=None,
            title="photo",
            body=None,
        ),
    ]
    unread = [
        SmdNotification(
            id=1,
            kind=EVENT_INCOMING_CALL,
            created_at=None,
            title="unread",
            body=None,
        )
    ]

    merged = merge_notifications(unread, history)

    assert [item.id for item in merged] == [1, 2]
    assert merged[0].title == "unread"
