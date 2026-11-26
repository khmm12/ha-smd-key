"""Notification event platform for SMD D-KEYS."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SmdDKeysConfigEntry
from .const import (
    DOMAIN,
    EVENT_GUEST_PHOTO,
    EVENT_INCOMING_CALL,
    EVENT_MESSAGE,
    EVENT_OTHER,
)
from .models import SmdNotification
from .notification_coordinator import SmdNotificationsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmdDKeysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the SMD notification event entity."""
    async_add_entities([SmdDKeysNotificationEvent(entry)])


class SmdDKeysNotificationEvent(
    CoordinatorEntity[SmdNotificationsCoordinator], EventEntity
):
    """A discrete event for each new SMD notification."""

    _attr_has_entity_name = True
    _attr_translation_key = "notification"
    _attr_event_types: ClassVar[list[str]] = [
        EVENT_INCOMING_CALL,
        EVENT_GUEST_PHOTO,
        EVENT_MESSAGE,
        EVENT_OTHER,
    ]

    def __init__(self, entry: SmdDKeysConfigEntry) -> None:
        """Initialize the notification event entity."""
        coordinator = entry.runtime_data.notifications
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_notification_event"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="SMD",
            model="D-KEYS intercom",
            name=entry.title,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fire one HA event per newly seen SMD notification."""
        data = self.coordinator.data
        if data is not None:
            for notification in data.new:
                self._trigger_event(notification.kind, _event_attributes(notification))
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Emit notifications that arrived before the entity was added."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()


def _event_attributes(notification: SmdNotification) -> dict[str, str | int]:
    """Return safe event attributes without SIP or file credentials."""
    attributes: dict[str, str | int] = {"notification_id": notification.id}
    if notification.created_at:
        attributes["created_at"] = notification.created_at
    if notification.title:
        attributes["title"] = notification.title
    if notification.body:
        attributes["body"] = notification.body
    if notification.caller:
        attributes["caller"] = notification.caller
    if notification.door_id:
        attributes["door_id"] = notification.door_id
    return attributes
