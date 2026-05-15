"""Camera broadcast actions for the SMD D-KEYS API."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from urllib.parse import quote

from ..models import SmdCamera, SmdDoor
from . import helpers
from .base import SmdBaseClient
from .errors import SmdMalformedResponseError

_LOGGER = logging.getLogger(__name__)


class SmdCameraActions(SmdBaseClient):
    """Camera discovery and stream source actions."""

    async def async_get_cameras(self, doors: Mapping[str, SmdDoor]) -> list[SmdCamera]:
        """Fetch the account's live broadcast camera list."""
        payload = await self._post_mde_form(self._common_params({"action": "getVideo"}))
        self._raise_for_error(payload, authenticated=True)
        doors_by_code_key = {
            door.code_key: door for door in doors.values() if door.code_key is not None
        }
        doors_by_code_mp = {
            door.code_mp: door for door in doors.values() if door.code_mp is not None
        }
        try:
            cameras = [
                helpers.camera_from_broadcast(item, doors_by_code_key, doors_by_code_mp)
                for item in helpers.expect_list(payload.get("DATA"), "DATA")
                if helpers.broadcast_metadata(item) is not None
            ]
        except SmdMalformedResponseError:
            _LOGGER.warning(
                "SMD getVideo response had an unexpected shape: %s",
                helpers.safe_payload_summary(payload),
            )
            raise
        _LOGGER.debug(
            "SMD camera discovery completed: count=%s linked=%s",
            len(cameras),
            sum(1 for camera in cameras if camera.door_id in doors),
        )
        return cameras

    async def async_get_camera_for_door(self, door: SmdDoor) -> SmdCamera | None:
        """Fetch live broadcast metadata for a video-capable door."""
        if not door.code_key or not door.has_option(helpers.VIDEO_OPTION):
            return None

        payload = await self._post_mde_form(
            self._common_params(
                {
                    "action": "getNewVideo",
                    "codeKey": door.code_key,
                }
            )
        )
        self._raise_for_error(payload, authenticated=True)
        try:
            data = helpers.broadcast_metadata(payload.get("DATA"))
            if data is None:
                _LOGGER.debug(
                    "SMD getNewVideo returned no broadcast metadata: door_id=%s",
                    door.id,
                )
                return None
            code_key = helpers.expect_text(data.get("codeKey"), "DATA.codeKey")
            code_mp = helpers.expect_text(data.get("codeMP"), "DATA.codeMP")
            srv = helpers.expect_text(data.get("srv"), "DATA.srv")
            protocol = (
                helpers.optional_text(data.get("protocol")) or helpers.RTSP_PROTOCOL
            )
        except SmdMalformedResponseError:
            _LOGGER.warning(
                "SMD getNewVideo response had an unexpected shape: %s",
                helpers.safe_payload_summary(payload),
            )
            raise

        return helpers.camera_from_metadata(
            data,
            door_id=door.id,
            fallback_title=door.title,
            fallback_address=door.address,
            code_key=code_key,
            code_mp=code_mp,
            srv=srv,
            protocol=protocol,
        )

    async def async_get_camera_stream_source(self, camera: SmdCamera) -> str:
        """Fetch an expiring RTSP source URL for a live video broadcast."""
        server_url = self._video_server_url(camera.srv)
        _LOGGER.debug(
            "Requesting SMD camera stream credentials: camera_id=%s server=%s",
            camera.id,
            camera.srv,
        )
        payload = await self._post_json(
            f"{server_url}/app/getVideoBroadcastByProtocol",
            self._common_params(
                {
                    "action": "getVideoBroadcastByProtocol",
                    "codeMP": camera.code_mp,
                    "protocol": helpers.RTSP_PROTOCOL,
                }
            ),
        )
        self._raise_for_error(payload, authenticated=True)
        try:
            data = helpers.expect_mapping(payload.get("DATA"), "DATA")
            login = helpers.expect_text(data.get("login"), "DATA.login")
            password = helpers.expect_text(data.get("password"), "DATA.password")
            url = helpers.expect_text(data.get("url"), "DATA.url")
        except SmdMalformedResponseError:
            _LOGGER.warning(
                "SMD getVideoBroadcastByProtocol response had an unexpected shape: %s",
                helpers.safe_payload_summary(payload),
            )
            raise

        stream_target = url.removeprefix("rtsp://")
        quoted_login = quote(login, safe="")
        quoted_password = quote(password, safe="")
        _LOGGER.debug("SMD camera stream credentials accepted: camera_id=%s", camera.id)
        return f"rtsp://{quoted_login}:{quoted_password}@{stream_target}"

    def _video_server_url(self, server_name: str) -> str:
        """Resolve the L-server URL advertised by the broadcast metadata."""
        if server_name.startswith(("http://", "https://")):
            return server_name.rstrip("/")
        if server_url := self._server_urls.get(server_name.upper()):
            return server_url
        raise SmdMalformedResponseError(f"SMD video server is unknown: {server_name}")
