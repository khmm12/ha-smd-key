"""Push notification actions for the SMD D-KEYS API."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from ..const import EVENT_GUEST_PHOTO, EVENT_INCOMING_CALL, EVENT_MESSAGE
from ..models import SmdDoor, SmdNotification
from . import helpers
from .base import SmdBaseClient
from .errors import SmdMalformedResponseError

_LOGGER = logging.getLogger(__name__)

UNREAD_NOTIFICATIONS_PATH = "/notification/getUnread"
ALL_NOTIFICATIONS_PATH = "/notification/getAll"
CALL_ACTION = "receiveCall"
PHOTO_FILE_TYPE = "image"


class SmdNotificationActions(SmdBaseClient):
    """Account notification polling and guest photo downloads."""

    async def async_get_unread_notifications(
        self, doors: Mapping[str, SmdDoor]
    ) -> list[SmdNotification]:
        """Fetch notifications that SMD still considers unread."""
        return await self._async_get_notifications(UNREAD_NOTIFICATIONS_PATH, doors)

    async def async_get_all_notifications(
        self, doors: Mapping[str, SmdDoor]
    ) -> list[SmdNotification]:
        """Fetch the server-side notification history."""
        return await self._async_get_notifications(ALL_NOTIFICATIONS_PATH, doors)

    async def async_get_notification_image(
        self, notification: SmdNotification
    ) -> bytes | None:
        """Download a guest photo from its signed HTTPS URL."""
        url = notification.file_url
        if not url or not url.startswith("https://"):
            return None
        return await self._request_bytes("GET", url)

    async def _async_get_notifications(
        self, path: str, doors: Mapping[str, SmdDoor]
    ) -> list[SmdNotification]:
        """Fetch and parse a notification list endpoint."""
        payload = await self._post_json(
            f"{self.push_url}{path}", self._common_params({})
        )
        self._raise_for_error(payload, authenticated=True)
        try:
            data = helpers.expect_mapping(payload.get("DATA"), "DATA")
            items = helpers.expect_list(data.get("list"), "DATA.list")
            notifications = [
                notification
                for item in items
                if (notification := _notification_from_server(item, doors)) is not None
            ]
        except SmdMalformedResponseError:
            _LOGGER.warning(
                "SMD notification response had an unexpected shape: %s",
                helpers.safe_payload_summary(payload),
            )
            raise
        _LOGGER.debug(
            "SMD notification poll completed: path=%s count=%s",
            path,
            len(notifications),
        )
        return sorted(notifications, key=lambda item: item.id)


def _notification_from_server(
    raw_value: helpers.JsonValue, doors: Mapping[str, SmdDoor]
) -> SmdNotification | None:
    """Convert one server notification entry into a runtime model."""
    raw = helpers.expect_mapping(raw_value, "DATA.list[]")
    notification_id = raw.get("ID")
    if not isinstance(notification_id, int):
        return None
    payload = _parse_object(raw.get("textPUSH")) or {}
    created_at = _clean_text(payload.get("dateTime")) or _clean_text(
        raw.get("createDateTime")
    )
    title = _clean_text(payload.get("title"))
    body = _clean_text(payload.get("body")) or _clean_text(payload.get("text"))

    if payload.get("action") == CALL_ACTION:
        return SmdNotification(
            id=notification_id,
            kind=EVENT_INCOMING_CALL,
            created_at=created_at,
            title=title or "Incoming call",
            body=body,
            caller=_clean_text(payload.get("fsCaller")),
            door_id=_door_id_for_code_mp(payload.get("codeMP"), doors),
        )

    file_data = _parse_object(payload.get("file")) or {}
    file_type = (_clean_text(file_data.get("typeFile")) or "").lower()
    file_url = _clean_text(file_data.get("url"))
    if file_type == PHOTO_FILE_TYPE:
        return SmdNotification(
            id=notification_id,
            kind=EVENT_GUEST_PHOTO,
            created_at=created_at,
            title=title,
            body=body,
            file_url=file_url if file_url and file_url.startswith("https://") else None,
        )

    return SmdNotification(
        id=notification_id,
        kind=EVENT_MESSAGE,
        created_at=created_at,
        title=title,
        body=body,
    )


def _parse_object(value: Any) -> dict[str, Any] | None:
    """Parse a JSON object that may be stored as a JSON string."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except ValueError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _clean_text(value: Any) -> str | None:
    """Trim SMD's quoted strings and drop empty values."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip().strip('"').strip()
    return cleaned or None


def _door_id_for_code_mp(code_mp: Any, doors: Mapping[str, SmdDoor]) -> str | None:
    """Map a notification codeMP value to a configured door."""
    if not isinstance(code_mp, str) or not code_mp:
        return None
    for door in doors.values():
        if door.code_mp == code_mp:
            return door.id
    return None
