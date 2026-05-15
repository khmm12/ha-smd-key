"""Set up the SMD D-KEYS integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmdAuthError, SmdConnectionError, SmdDKeysClient
from .const import CONF_CMDC_URL, CONF_L2_URL, CONF_PHONE, CONF_TOKEN, DOMAIN
from .coordinator import SmdDKeysCoordinator
from .models import SmdDKeysRuntimeData

PLATFORMS: list[Platform] = [Platform.CAMERA, Platform.LOCK]
_LOGGER = logging.getLogger(__name__)

type SmdDKeysConfigEntry = ConfigEntry[SmdDKeysRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: SmdDKeysConfigEntry) -> bool:
    """Set up SMD D-KEYS from a config entry."""
    _LOGGER.debug("Setting up SMD D-KEYS entry %s", entry.entry_id)
    client = SmdDKeysClient(
        async_get_clientsession(hass),
        phone=entry.data[CONF_PHONE],
        token=entry.data[CONF_TOKEN],
        cmdc_url=entry.data.get(CONF_CMDC_URL),
        l2_url=entry.data.get(CONF_L2_URL),
    )
    coordinator = SmdDKeysCoordinator(hass, entry, client)
    entry.runtime_data = SmdDKeysRuntimeData(client=client, coordinator=coordinator)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    try:
        await coordinator.async_config_entry_first_refresh()
    except SmdAuthError:
        raise
    except SmdConnectionError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
        ) from err

    _LOGGER.debug(
        "SMD D-KEYS first refresh completed for entry %s: doors=%s",
        entry.entry_id,
        len(coordinator.data or {}),
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmdDKeysConfigEntry) -> bool:
    """Unload a SMD D-KEYS config entry."""
    _LOGGER.debug("Unloading SMD D-KEYS entry %s", entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: SmdDKeysConfigEntry) -> None:
    """Reload a SMD D-KEYS config entry."""
    _LOGGER.debug("Reloading SMD D-KEYS entry %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
