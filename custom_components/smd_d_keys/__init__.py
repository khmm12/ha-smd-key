"""Set up the SMD D-KEYS integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import SmdAuthError, SmdConnectionError, SmdDKeysClient
from .api.tls import smd_ssl_context
from .const import CONF_CMDC_URL, CONF_L2_URL, CONF_PHONE, CONF_TOKEN, DOMAIN
from .coordinator import SmdDKeysCoordinator
from .models import SmdDKeysRuntimeData
from .notification_coordinator import (
    LAST_NOTIFICATION_ID,
    NOTIFICATION_STORE_VERSION,
    SmdNotificationsCoordinator,
)

PLATFORMS: list[Platform] = [
    Platform.CAMERA,
    Platform.EVENT,
    Platform.IMAGE,
    Platform.LOCK,
]
_LOGGER = logging.getLogger(__name__)

type SmdDKeysConfigEntry = ConfigEntry[SmdDKeysRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: SmdDKeysConfigEntry) -> bool:
    """Set up SMD D-KEYS from a config entry."""
    _LOGGER.debug("Setting up SMD D-KEYS entry %s", entry.entry_id)
    ssl_context = await hass.async_add_executor_job(smd_ssl_context)
    client = SmdDKeysClient(
        async_get_clientsession(hass),
        phone=entry.data[CONF_PHONE],
        token=entry.data[CONF_TOKEN],
        cmdc_url=entry.data.get(CONF_CMDC_URL),
        l2_url=entry.data.get(CONF_L2_URL),
        ssl_context=ssl_context,
    )
    coordinator = SmdDKeysCoordinator(hass, entry, client)
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

    notification_store: Store[dict[str, int]] = Store(
        hass,
        NOTIFICATION_STORE_VERSION,
        f"{DOMAIN}.{entry.entry_id}.notifications",
    )
    stored_notifications = await notification_store.async_load() or {}
    last_notification_id = stored_notifications.get(LAST_NOTIFICATION_ID)
    notifications = SmdNotificationsCoordinator(
        hass,
        entry,
        client,
        notification_store,
        coordinator.data or {},
        last_notification_id,
    )
    entry.runtime_data = SmdDKeysRuntimeData(
        client=client,
        coordinator=coordinator,
        notifications=notifications,
    )
    entry.async_create_background_task(
        hass,
        notifications.async_refresh(),
        "smd_d_keys notifications first refresh",
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
