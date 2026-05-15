"""Door-key actions for the SMD D-KEYS API."""

from __future__ import annotations

import logging

from ..models import SmdDoor
from . import helpers
from .base import SmdBaseClient
from .errors import SmdMalformedResponseError
from .helpers import JsonValue

_LOGGER = logging.getLogger(__name__)


class SmdDoorActions(SmdBaseClient):
    """Door discovery and open-command actions."""

    async def async_get_doors(self) -> list[SmdDoor]:
        """Fetch the account's regular door keys."""
        payload = await self._post_mde_form(self._common_params({"action": "getKey"}))
        self._raise_for_error(payload, authenticated=True)
        try:
            doors = [
                await self._door_from_key_with_options(item)
                for item in helpers.expect_list(payload.get("DATA"), "DATA")
            ]
        except SmdMalformedResponseError:
            _LOGGER.warning(
                "SMD getKey response had an unexpected shape: %s",
                helpers.safe_payload_summary(payload),
            )
            raise
        _LOGGER.debug(
            "SMD door discovery completed: count=%s open_ready=%s video_capable=%s",
            len(doors),
            sum(1 for door in doors if door.mqtt_topic and door.command),
            sum(1 for door in doors if door.has_option(helpers.VIDEO_OPTION)),
        )
        return doors

    async def async_open_door(self, door: SmdDoor) -> None:
        """Send the open-door command for a door."""
        if not door.mqtt_topic or not door.command:
            _LOGGER.debug("Opening SMD door via legacy L2 flow: door_id=%s", door.id)
            await self._async_open_legacy_l2_door(door)
            return
        _LOGGER.debug("Opening SMD door via CMDC flow: door_id=%s", door.id)
        payload = await self._post_json(
            f"{self.cmdc_url}/openDoor",
            self._common_params(
                {
                    "action": "openDoor",
                    "topic": door.mqtt_topic,
                    "command": door.command,
                    "uid": helpers.uid_from_topic(door.mqtt_topic),
                }
            ),
        )
        self._raise_for_error(payload, authenticated=True)
        _LOGGER.debug("SMD CMDC open-door response accepted: door_id=%s", door.id)

    async def _async_open_legacy_l2_door(self, door: SmdDoor) -> None:
        """Open a door through the legacy L2 payload used by older app flows."""
        topic = door.mqtt_topic
        if not topic:
            raise SmdMalformedResponseError("SMD door has no open topic")
        payload = await self._request_json(
            "POST",
            f"{self.l2_url}/",
            data={
                "action": "openDoor",
                "token": self.token,
                "topic": topic,
                "text": door.command or "cmd1",
            },
        )
        self._raise_for_error(payload, authenticated=True)

    async def _door_from_key_with_options(self, raw_value: JsonValue) -> SmdDoor:
        """Convert a key and fetch missing MQTT option data when needed."""
        raw = helpers.expect_mapping(raw_value, "DATA[]")
        door = helpers.door_from_key(raw)
        if door.mqtt_topic or not helpers.key_has_option(raw, "mqtt"):
            return door
        if not door.code_key:
            return door

        _LOGGER.debug("Fetching SMD MQTT option for door_id=%s", door.id)
        option_payload = await self._post_mde_form(
            self._common_params(
                {
                    "action": "getDataOption",
                    "option": "mqtt",
                    "codeKey": door.code_key,
                }
            )
        )
        self._raise_for_error(option_payload, authenticated=True)
        data = helpers.expect_mapping(option_payload.get("DATA"), "DATA")
        mqtt = helpers.expect_mapping(data.get("mqtt"), "DATA.mqtt")
        return door.with_open_command(
            mqtt_topic=helpers.optional_text(mqtt.get("topicCommand")),
            command=helpers.optional_text(mqtt.get("openCommand")),
        )
