"""Coordinator for SMD D-KEYS."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmdApiError, SmdAuthError, SmdConnectionError, SmdDKeysClient
from .const import DOMAIN, NAME
from .models import SmdDoor

_LOGGER = logging.getLogger(__name__)


class SmdDKeysCoordinator(DataUpdateCoordinator[dict[str, SmdDoor]]):
    """Fetch SMD account doors and surface auth failures."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SmdDKeysClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=NAME,
            update_interval=timedelta(minutes=30),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, SmdDoor]:
        """Fetch current account doors."""
        _LOGGER.debug("Refreshing SMD account doors")
        try:
            await self.client.async_get_servers()
            doors = await self.client.async_get_doors()
        except SmdAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err
        except SmdConnectionError as err:
            raise UpdateFailed("Failed to connect to SMD") from err
        except SmdApiError as err:
            raise UpdateFailed("SMD API request failed") from err
        _LOGGER.debug("SMD account door refresh completed: count=%s", len(doors))
        return {door.id: door for door in doors}
