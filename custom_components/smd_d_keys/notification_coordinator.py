"""Coordinator for SMD D-KEYS push notifications."""

from __future__ import annotations

import logging
import time
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
FULL_SYNC_SECONDS = 900


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
        self._last_notification_id = normalize_last_notification_id(
            last_notification_id
        )
        self._last_full_sync: float | None = None

    async def _async_update_data(self) -> SmdNotificationsData:
        """Fetch unread notifications and periodically reconcile history."""
        try:
            unread = await self.client.async_get_unread_notifications(self._doors)
        except SmdAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err
        except (SmdConnectionError, SmdApiError) as err:
            raise UpdateFailed("Failed to fetch SMD notifications") from err

        history: list[SmdNotification] = []
        now = time.monotonic()
        if (
            self._last_full_sync is None
            or now - self._last_full_sync >= FULL_SYNC_SECONDS
        ):
            try:
                history = await self.client.async_get_all_notifications(self._doors)
            except (SmdConnectionError, SmdApiError) as err:
                _LOGGER.debug(
                    "SMD notification history sync failed: %s", type(err).__name__
                )
            else:
                self._last_full_sync = now

        if self._last_notification_id is None and self._last_full_sync is None:
            raise UpdateFailed("Initial SMD notification history sync failed")

        merged = merge_notifications(unread, history)
        if self._last_notification_id is None:
            new, newest = filter_new_notifications(merged, None)
            self._last_notification_id = newest
            await self._async_save_last_id()
            return SmdNotificationsData(notifications=merged, new=new)

        new, newest = filter_new_notifications(merged, self._last_notification_id)
        if new:
            self._last_notification_id = newest
            await self._async_save_last_id()
        return SmdNotificationsData(
            notifications=merged,
            new=sorted(new, key=lambda item: item.id),
        )

    async def _async_save_last_id(self) -> None:
        """Persist the newest seen notification ID."""
        assert self._last_notification_id is not None
        data = {LAST_NOTIFICATION_ID: self._last_notification_id}
        self._store.data = data
        await self._store.async_save(data)


def normalize_last_notification_id(value: int | None) -> int | None:
    """Treat a stored zero as uninitialized so history is not replayed."""
    return value or None


def filter_new_notifications(
    notifications: list[SmdNotification], last_notification_id: int | None
) -> tuple[list[SmdNotification], int]:
    """Return notifications newer than the stored ID and the newest ID."""
    if last_notification_id is None:
        return [], max((item.id for item in notifications), default=0)
    new = [item for item in notifications if item.id > last_notification_id]
    return new, max((item.id for item in new), default=last_notification_id)


def merge_notifications(
    unread: list[SmdNotification], history: list[SmdNotification]
) -> list[SmdNotification]:
    """Merge unread and history entries by ID, preferring unread data."""
    merged = {item.id: item for item in history}
    merged.update({item.id: item for item in unread})
    return sorted(merged.values(), key=lambda item: item.id)
