"""The Stromnetz Graz integration."""
from __future__ import annotations

import asyncio
import logging
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
)

from sngraz import StromNetzGraz, InvalidLogin
from .const import DOMAIN

PLATFORMS = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Stromnetz Graz from a config entry."""

    async def _async_delayed_setup(*_):
        """Run the actual connection and sensor setup in the background."""
        conn = StromNetzGraz(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

        try:
            await conn.authenticate()
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout connecting: %s", err)
            return
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting: %s ", err)
            return
        except InvalidLogin as err:
            _LOGGER.error("Invalid Auth: %s", err)
            return
        except Exception as exp:
            _LOGGER.error("Failed to login. %s", exp)
            return

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # If HA is already running (e.g., you click 'Reload' in the UI), run it immediately
    if hass.is_running:
        hass.async_create_task(_async_delayed_setup())
    else:
        # Otherwise, wait for HA to fully boot before starting the network calls
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_delayed_setup)

    return True


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok and DOMAIN in hass.data:
        await hass.data[DOMAIN].close_connection()
        hass.data.pop(DOMAIN)

    return unload_ok
