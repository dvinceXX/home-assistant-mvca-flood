"""The MVCA Flood & Low Water integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import MVCADataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]

# Keep this alias available to the sensor platform and other modules.
MVCAConfigEntry = ConfigEntry


def _get_scan_interval(entry: MVCAConfigEntry) -> int:
    """Return a valid polling interval from the config entry."""
    try:
        interval = int(
            entry.options.get(
                CONF_SCAN_INTERVAL,
                entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )
    except (TypeError, ValueError):
        return DEFAULT_SCAN_INTERVAL

    if not 5 <= interval <= 1440:
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

    # Do not forward the platform if the first refresh fails.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
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