"""The MVCA Flood & Low Water integration."""

from __future__ import annotations

import logging
from typing import TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import MVCADataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

MVCAConfigEntry: TypeAlias = ConfigEntry


def _get_scan_interval(entry: MVCAConfigEntry) -> int:
    """Return a valid polling interval from the config entry."""
    value = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    try:
        interval = int(value)
    except (TypeError, ValueError):
        _LOGGER.warning(
            "Invalid MVCA scan interval %r; using default %s minutes",
            value,
            DEFAULT_SCAN_INTERVAL,
        )
        return DEFAULT_SCAN_INTERVAL

    if not 5 <= interval <= 1440:
        _LOGGER.warning(
            "MVCA scan interval %s is outside 5–1440 minutes; "
            "using default %s minutes",
            interval,
            DEFAULT_SCAN_INTERVAL,
        )
        return DEFAULT_SCAN_INTERVAL

    return interval


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MVCAConfigEntry,
) -> bool:
    """Set up MVCA Flood & Low Water from a config entry."""
    coordinator = MVCADataUpdateCoordinator(
        hass,
        scan_interval=_get_scan_interval(entry),
    )

    # Require a successful first refresh before creating entities.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )

    _LOGGER.debug(
        "Setting up MVCA sensor platform; data keys: %s",
        list(coordinator.data or {}),
    )

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: MVCAConfigEntry,
) -> bool:
    """Unload the integration's platforms."""
    return await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )


async def _async_update_listener(
    hass: HomeAssistant,
    entry: MVCAConfigEntry,
) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)