"""Guest photo image platform for SMD D-KEYS."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import SmdDKeysConfigEntry
from .api import SmdApiError, SmdConnectionError
from .const import DOMAIN, EVENT_GUEST_PHOTO
from .device import account_device_info
from .models import SmdNotification
from .notification_coordinator import SmdNotificationsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmdDKeysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the SMD last guest photo image entity."""
    async_add_entities([SmdDKeysLastGuestPhoto(entry)])


class SmdDKeysLastGuestPhoto(
    CoordinatorEntity[SmdNotificationsCoordinator], ImageEntity
):
    """The most recent guest photo pushed by SMD."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_guest_photo"

    def __init__(self, entry: SmdDKeysConfigEntry) -> None:
        """Initialize the guest photo image entity."""
        coordinator = entry.runtime_data.notifications
        super().__init__(coordinator)
        ImageEntity.__init__(self, coordinator.hass)
        self._client = entry.runtime_data.client
        self._image: bytes | None = None
        self._load_lock = asyncio.Lock()
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_last_guest_photo"
        self._attr_device_info = account_device_info(entry)

    async def async_image(self) -> bytes | None:
        """Return the last downloaded guest photo."""
        return self._image

    @callback
    def _handle_coordinator_update(self) -> None:
        """Download newly pushed guest photos."""
        data = self.coordinator.data
        if data is not None:
            photos = [
                notification
                for notification in data.new
                if notification.kind == EVENT_GUEST_PHOTO and notification.file_url
            ]
            if photos:
                self.hass.async_create_task(
                    self._async_load_photo(photos[-1]),
                    "smd_d_keys load guest photo",
                )
        self.async_write_ha_state()

    async def _async_load_photo(self, notification: SmdNotification) -> None:
        """Download one guest photo without blocking the event loop."""
        async with self._load_lock:
            try:
                image = await self._client.async_get_notification_image(notification)
            except (SmdConnectionError, SmdApiError) as err:
                _LOGGER.warning(
                    "Could not download SMD guest photo %s: %s",
                    notification.id,
                    type(err).__name__,
                )
                return
            if image is None:
                return
            self._image = image
            self._attr_image_last_updated = dt_util.utcnow()
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Download a photo that arrived before the entity was added."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
