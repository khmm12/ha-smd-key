"""DTO conversion and validation helpers for the SMD D-KEYS API."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Any
from urllib.parse import urlsplit

from ..models import SmdCamera, SmdDoor
from .errors import SmdMalformedResponseError

RUSSIAN_PHONE_DIGITS = 11
CALL_CODE_DIGITS = 6
VIDEO_OPTION = "videoTranslate"
RTSP_PROTOCOL = "RTSP"

type JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None
type JsonObject = dict[str, JsonValue]


def normalize_phone(phone: str) -> str:
    """Normalize a phone number like the Android app's stored digits."""
    digits = "".join(char for char in phone if char.isdigit())
    if len(digits) == RUSSIAN_PHONE_DIGITS and digits.startswith("8"):
        return f"7{digits[1:]}"
    return digits


def normalize_call_code(call_code: str) -> str:
    """Normalize the call-code value before sending it as SMD's `otp` field."""
    return "".join(char for char in call_code if char.isdigit())


def door_from_key(raw_value: JsonValue) -> SmdDoor:
    """Convert a `KeyDto`-shaped mapping into a runtime door model."""
    raw = expect_mapping(raw_value, "DATA[]")
    mqtt_topic = optional_text(raw.get("mqtt"))
    command = optional_text(raw.get("text"))
    title = str(raw.get("Nickname") or raw.get("Address") or "SMD Door")
    code_key = optional_text(raw.get("codeKey"))
    code_mp = optional_text(raw.get("codeMP"))
    source_id = str(raw.get("uid") or mqtt_topic or code_key or code_mp or title)
    return SmdDoor(
        id=hash_identifier(source_id),
        title=title,
        address=optional_text(raw.get("Address")),
        code_key=code_key,
        mqtt_topic=mqtt_topic,
        command=command,
        uid=optional_text(raw.get("uid")),
        code_mp=code_mp,
        room_number=optional_text(raw.get("roomNumber")),
        options=options_from_key(raw),
    )


def camera_from_broadcast(
    raw_value: JsonValue,
    doors_by_code_key: Mapping[str, SmdDoor],
    doors_by_code_mp: Mapping[str, SmdDoor],
) -> SmdCamera:
    """Convert a `BroadcastDto`-shaped mapping into a runtime camera model."""
    data = broadcast_metadata(raw_value)
    if data is None:
        raise SmdMalformedResponseError("SMD broadcast metadata is empty")
    code_key = expect_text(data.get("codeKey"), "DATA.codeKey")
    code_mp = expect_text(data.get("codeMP"), "DATA.codeMP")
    srv = expect_text(data.get("srv"), "DATA.srv")
    protocol = optional_text(data.get("protocol")) or RTSP_PROTOCOL
    door = doors_by_code_key.get(code_key) or doors_by_code_mp.get(code_mp)
    return camera_from_metadata(
        data,
        door_id=door.id if door is not None else hash_identifier(code_key),
        fallback_title=door.title if door is not None else "SMD Camera",
        fallback_address=door.address if door is not None else None,
        code_key=code_key,
        code_mp=code_mp,
        srv=srv,
        protocol=protocol,
    )


def camera_from_metadata(
    data: Mapping[str, Any],
    *,
    door_id: str,
    fallback_title: str,
    fallback_address: str | None,
    code_key: str,
    code_mp: str,
    srv: str,
    protocol: str,
) -> SmdCamera:
    """Build a camera model from broadcast metadata."""
    return SmdCamera(
        id=hash_identifier(str(data.get("UID") or code_key or code_mp)),
        door_id=door_id,
        title=optional_text(data.get("Nickname")) or fallback_title,
        address=optional_text(data.get("Address")) or fallback_address,
        code_key=code_key,
        code_mp=code_mp,
        srv=srv,
        protocol=protocol,
        uid=optional_text(data.get("UID")),
        online=optional_bool(data.get("Online")),
    )


def hash_identifier(value: str) -> str:
    """Hash a sensitive stable identifier for HA unique IDs/options."""
    return sha256(value.encode()).hexdigest()[:16]


def uid_from_topic(topic: str) -> str:
    """Return Kotlin substringAfter(topic, '/') semantics."""
    if "/" not in topic:
        return topic
    return topic.split("/", 1)[1]


def is_error(value: Any) -> bool:
    """Return whether an API `error` value means failure."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


def key_has_option(raw: Mapping[str, Any], option: str) -> bool:
    """Return whether a raw key advertises an option."""
    return option in options_from_key(raw)


def options_from_key(raw: Mapping[str, Any]) -> tuple[str, ...]:
    """Return advertised key options from the known Android DTO fields."""
    result: list[str] = []
    for field in ("options_exist", "options"):
        options = raw.get(field)
        if isinstance(options, list):
            result.extend(str(item) for item in options if isinstance(item, str))
    return tuple(dict.fromkeys(result))


def looks_like_auth_error(message: str) -> bool:
    """Heuristic for token/session failures; exact server text needs live validation."""
    normalized = message.lower()
    return any(token in normalized for token in ("token", "auth", "login", "session"))


def request_action(kwargs: Mapping[str, Any]) -> str | None:
    """Return the non-sensitive SMD action name from a request."""
    payload = kwargs.get("data") or kwargs.get("json")
    if not isinstance(payload, Mapping):
        return None
    action = payload.get("action")
    return action if isinstance(action, str) else None


def safe_url_summary(url: str) -> str:
    """Return a URL summary without user credentials or query parameters."""
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def safe_payload_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize an SMD response without phone, token, code, or door data."""
    data = payload.get("DATA")
    if isinstance(data, Mapping):
        data_summary: Any = {"type": "object", "keys": sorted(str(key) for key in data)}
    elif isinstance(data, list):
        data_summary = {"type": "list", "len": len(data)}
    else:
        data_summary = type(data).__name__

    summary: dict[str, Any] = {
        "error": payload.get("error"),
        "DATA": data_summary,
    }
    for field in ("message", "warning", "critical"):
        if payload.get(field):
            summary[f"has_{field}"] = True
    return {key: value for key, value in summary.items() if value not in (None, "")}


def expect_mapping(value: JsonValue, field: str) -> dict[str, Any]:
    """Return a mapping or raise a malformed-response error."""
    if not isinstance(value, dict):
        raise SmdMalformedResponseError(f"SMD field {field} is missing or invalid")
    return value


def expect_list(value: JsonValue, field: str) -> list[JsonValue]:
    """Return a list or raise a malformed-response error."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise SmdMalformedResponseError(f"SMD field {field} is not a list")
    return value


def expect_text(value: JsonValue, field: str) -> str:
    """Return a non-empty text field or raise a malformed-response error."""
    if not isinstance(value, str) or not value:
        raise SmdMalformedResponseError(f"SMD field {field} is missing")
    return value


def optional_text(value: JsonValue) -> str | None:
    """Return a string value when present."""
    return value if isinstance(value, str) and value else None


def broadcast_metadata(value: JsonValue) -> dict[str, Any] | None:
    """Return broadcast metadata, accepting both DTO object and list shapes."""
    if isinstance(value, list):
        if not value:
            return None
        value = value[0]
    data = expect_mapping(value, "DATA")
    required_fields = ("codeKey", "codeMP", "srv")
    if not any(optional_text(data.get(field)) for field in required_fields):
        return None
    return data


def optional_bool(value: JsonValue) -> bool | None:
    """Return a boolean-ish SMD value when present."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return None
