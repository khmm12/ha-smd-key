"""Coordinator for SMD D-KEYS push notifications."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SmdApiError,
    SmdAuthError,
    SmdConnectionError,
    SmdDKeysClient,
)
from .const import DOMAIN, NOTIFICATION_POLL_SECONDS
from .models import SmdDoor, SmdNotification, SmdNotificationsData

_LOGGER = logging.getLogger(__name__)

NOTIFICATION_STORE_VERSION = 1
LAST_NOTIFICATION_ID = "last_notification_id"


class SmdNotificationsCoordinator(DataUpdateCoordinator[SmdNotificationsData]):
    """Poll SMD notifications and emit only events that were not seen before."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SmdDKeysClient,
        store: Store[dict[str, int]],
        doors: dict[str, SmdDoor],
        last_notification_id: int | None,
    ) -> None:
        """Initialize the notifications coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_notifications",
            update_interval=timedelta(seconds=NOTIFICATION_POLL_SECONDS),
            always_update=False,
        )
        self.client = client
        self._store = store
        self._doors = doors
        self._last_notification_id = last_notification_id

    async def _async_update_data(self) -> SmdNotificationsData:
        """Fetch unread notifications and filter out already seen IDs."""
        try:
            notifications = await self.client.async_get_unread_notifications(
                self._doors
            )
        except SmdAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err
        except (SmdConnectionError, SmdApiError) as err:
            raise UpdateFailed("Failed to fetch SMD notifications") from err

        if self._last_notification_id is None:
            new, newest = filter_new_notifications(notifications, None)
            self._last_notification_id = newest
            await self._async_save_last_id()
            return SmdNotificationsData(notifications=notifications, new=new)

        new, newest = filter_new_notifications(
            notifications, self._last_notification_id
        )
        if new:
            self._last_notification_id = newest
            await self._async_save_last_id()
        return SmdNotificationsData(
            notifications=notifications,
            new=sorted(new, key=lambda item: item.id),
        )

    async def _async_save_last_id(self) -> None:
        """Persist the newest seen notification ID."""
        assert self._last_notification_id is not None
        data = {LAST_NOTIFICATION_ID: self._last_notification_id}
        self._store.data = data
        await self._store.async_save(data)


def filter_new_notifications(
    notifications: list[SmdNotification], last_notification_id: int | None
) -> tuple[list[SmdNotification], int]:
    """Return notifications newer than the stored ID and the newest ID."""
    if last_notification_id is None:
        return [], max((item.id for item in notifications), default=0)
    new = [item for item in notifications if item.id > last_notification_id]
    return new, max((item.id for item in new), default=last_notification_id)
