"""Camera platform for SMD D-KEYS."""

from __future__ import annotations

import logging

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SmdDKeysConfigEntry
from .api import SmdApiError, SmdAuthError, SmdConnectionError
from .const import CONF_SELECTED_DOORS, DOMAIN
from .coordinator import SmdDKeysCoordinator
from .models import SmdCamera

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmdDKeysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SMD D-KEYS camera entities."""
    coordinator = entry.runtime_data.coordinator
    selected = set(entry.options.get(CONF_SELECTED_DOORS, []))
    doors = coordinator.data or {}
    door_ids = set(doors)
    try:
        cameras = await coordinator.client.async_get_cameras(doors)
    except SmdAuthError as err:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN,
            translation_key="auth_failed",
        ) from err
    except SmdApiError as err:
        _LOGGER.warning("Could not fetch SMD camera list: %s", err)
        cameras = []

    entities = [
        SmdDKeysCamera(coordinator, camera)
        for camera in cameras
        if not selected or camera.door_id in selected or camera.door_id not in door_ids
    ]
    _LOGGER.debug(
        "Setting up SMD cameras: fetched=%s added=%s linked=%s selected=%s",
        len(cameras),
        len(entities),
        sum(1 for camera in cameras if camera.door_id in door_ids),
        len(selected) if selected else "all",
    )
    async_add_entities(entities)


class SmdDKeysCamera(Camera):
    """Live SMD intercom camera."""

    _attr_has_entity_name = True
    _attr_supported_features = CameraEntityFeature.STREAM
    _attr_translation_key = "camera"

    def __init__(
        self,
        coordinator: SmdDKeysCoordinator,
        camera: SmdCamera,
    ) -> None:
        """Initialize the camera."""
        super().__init__()
        self.coordinator = coordinator
        self._camera = camera
        door = (coordinator.data or {}).get(camera.door_id)
        self._linked_to_door = door is not None
        self._attr_unique_id = f"{DOMAIN}_{camera.id}_camera"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, camera.door_id)},
            manufacturer="SMD",
            model="D-KEYS intercom",
            name=door.title if door is not None else camera.title,
        )

    @property
    def available(self) -> bool:
        """Return whether the camera can be used."""
        data = self.coordinator.data or {}
        return (
            self.coordinator.last_update_success
            and (not self._linked_to_door or self._camera.door_id in data)
            and self._camera.online is not False
        )

    @property
    def use_stream_for_stills(self) -> bool:
        """Use the RTSP stream to generate camera proxy still images."""
        return True

    async def stream_source(self) -> str | None:
        """Return an RTSP stream source for Home Assistant/go2rtc."""
        _LOGGER.debug(
            "Requesting SMD camera stream source: camera_id=%s server=%s protocol=%s",
            self._camera.id,
            self._camera.srv,
            self._camera.protocol,
        )
        try:
            source = await self.coordinator.client.async_get_camera_stream_source(
                self._camera
            )
            _LOGGER.debug(
                "SMD camera stream source acquired: camera_id=%s",
                self._camera.id,
            )
            return source
        except SmdAuthError as err:
            self.coordinator.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err
        except SmdConnectionError as err:
            _LOGGER.warning("Could not fetch SMD camera stream source: %s", err)
            return None
        except SmdApiError as err:
            _LOGGER.warning("SMD rejected camera stream source request: %s", err)
            return None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return no still image for the live-stream-only MVP."""
        return None
