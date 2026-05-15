"""Lock platform for SMD D-KEYS."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later

from . import SmdDKeysConfigEntry
from .api import SmdApiError, SmdAuthError
from .const import CONF_RELOCK_DELAY, CONF_SELECTED_DOORS, DEFAULT_RELOCK_DELAY, DOMAIN
from .coordinator import SmdDKeysCoordinator
from .models import SmdDoor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmdDKeysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SMD D-KEYS lock entities."""
    coordinator = entry.runtime_data.coordinator
    selected = set(entry.options.get(CONF_SELECTED_DOORS, []))
    relock_delay = int(entry.options.get(CONF_RELOCK_DELAY, DEFAULT_RELOCK_DELAY))
    doors = coordinator.data or {}
    entities = [
        SmdDoorLock(coordinator, door, relock_delay)
        for door_id, door in doors.items()
        if not selected or door_id in selected
    ]
    _LOGGER.debug(
        "Setting up SMD locks: fetched=%s added=%s selected=%s relock_delay=%s",
        len(doors),
        len(entities),
        len(selected) if selected else "all",
        relock_delay,
    )
    async_add_entities(entities)


class SmdDoorLock(LockEntity):
    """An assumed-state SMD intercom lock."""

    _attr_assumed_state = True
    _attr_has_entity_name = True
    _attr_is_locked = True
    _attr_translation_key = "lock"

    def __init__(
        self,
        coordinator: SmdDKeysCoordinator,
        door: SmdDoor,
        relock_delay: int,
    ) -> None:
        """Initialize the lock."""
        self.coordinator = coordinator
        self._door = door
        self._relock_delay = relock_delay
        self._cancel_relock: Callable[[], None] | None = None
        self._attr_unique_id = f"{DOMAIN}_{door.id}"
        self._attr_name = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, door.id)},
            manufacturer="SMD",
            model="D-KEYS intercom",
            name=door.title,
        )

    @property
    def available(self) -> bool:
        """Return whether the door is still present in the latest account data."""
        data = self.coordinator.data or {}
        return self.coordinator.last_update_success and self._door.id in data

    async def async_unlock(self, **kwargs: Any) -> None:
        """Open the intercom door and temporarily report unlocked."""
        door = (self.coordinator.data or {}).get(self._door.id, self._door)
        _LOGGER.debug(
            "Sending SMD open-door command: door_id=%s has_mqtt=%s",
            door.id,
            bool(door.mqtt_topic and door.command),
        )
        try:
            await self.coordinator.client.async_open_door(door)
        except SmdAuthError as err:
            self.coordinator.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err
        except SmdApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="open_failed",
            ) from err

        _LOGGER.debug("SMD open-door command accepted: door_id=%s", door.id)
        self._attr_is_locked = False
        self._schedule_relock()
        self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        """Reset the local assumed state to locked."""
        self._mark_locked()

    async def async_will_remove_from_hass(self) -> None:
        """Cancel pending callbacks when HA removes the entity."""
        self._cancel_pending_relock()

    def _schedule_relock(self) -> None:
        """Schedule the assumed-state relock transition."""
        self._cancel_pending_relock()
        _LOGGER.debug(
            "Scheduling SMD assumed relock: door_id=%s delay=%s",
            self._door.id,
            self._relock_delay,
        )
        self._cancel_relock = async_call_later(
            self.hass,
            self._relock_delay,
            self._handle_relock,
        )

    @callback
    def _handle_relock(self, _: Any) -> None:
        """Handle the relock timer callback."""
        self._cancel_relock = None
        self._mark_locked()

    @callback
    def _mark_locked(self) -> None:
        """Mark the assumed state locked."""
        self._cancel_pending_relock()
        self._attr_is_locked = True
        if self.hass:
            self.async_write_ha_state()

    @callback
    def _cancel_pending_relock(self) -> None:
        """Cancel the pending relock callback."""
        if self._cancel_relock is None:
            return
        self._cancel_relock()
        self._cancel_relock = None
