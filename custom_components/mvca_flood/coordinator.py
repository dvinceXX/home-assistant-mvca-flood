"""Data coordinator for MVCA Flood & Low Water."""

from __future__ import annotations

from datetime import timedelta
import logging
import re

from aiohttp import ClientError, ClientTimeout
from bs4 import BeautifulSoup

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DASHBOARD_URL,
    DEFAULT_SCAN_INTERVAL,
    FLOOD_STATUSES,
    LOW_WATER_STATUSES,
    RIVER_CARP,
    RIVER_LOWER_OTTAWA,
    RIVER_MISSISSIPPI,
    TYPE_FLOOD,
    TYPE_LOW_WATER,
)

_LOGGER = logging.getLogger(__name__)

RIVERS = (
    (RIVER_MISSISSIPPI, "Mississippi River"),
    (RIVER_CARP, "Carp River"),
    (RIVER_LOWER_OTTAWA, "Lower Ottawa"),
)

# Compatibility alias used by the integration and sensor platform.
MVCAConfigEntry = ConfigEntry


class MVCADataUpdateCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Coordinate MVCA data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        if not isinstance(scan_interval, int) or isinstance(
            scan_interval, bool
        ):
            raise ValueError("scan_interval must be an integer")

        if not 5 <= scan_interval <= 1440:
            raise ValueError("scan_interval must be between 5 and 1440")

        self.hass = hass

        super().__init__(
            hass,
            logger=_LOGGER,
            name="MVCA Flood & Low Water",
            update_interval=timedelta(minutes=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, str]:
        """Fetch and parse MVCA dashboard data."""
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(
                DASHBOARD_URL,
                timeout=ClientTimeout(total=30),
                headers={
                    "User-Agent": "Home Assistant MVCA Flood & Low Water",
                },
            ) as response:
                response.raise_for_status()
                html = await response.text()

        except (ClientError, TimeoutError) as err:
            raise UpdateFailed(
                f"Unable to retrieve MVCA dashboard: {err}"
            ) from err

        # Temporary diagnostics: inspect what the server actually returned.
        soup = BeautifulSoup(html, "html.parser")
        _LOGGER.warning(
            "MVCA response title: %s",
            soup.title.get_text(" ", strip=True) if soup.title else None,
        )
        _LOGGER.warning(
            "MVCA headings: %s",
            [
                heading.get_text(" ", strip=True)
                for heading in soup.find_all(
                    ["h1", "h2", "h3", "h4", "h5", "h6"]
                )
            ],
        )
        _LOGGER.warning("MVCA response length: %d", len(html))

        try:
            data = self._parse_dashboard(html)
        except (ValueError, AttributeError, TypeError) as err:
            raise UpdateFailed(
                f"Unable to parse MVCA dashboard: {err}"
            ) from err

        _LOGGER.debug("Successfully updated MVCA status data")
        return data

    @classmethod
    def _parse_dashboard(cls, html: str) -> dict[str, str]:
        """Parse the six statuses from the MVCA dashboard."""
        if not html or not html.strip():
            raise ValueError("The MVCA dashboard response was empty")

        soup = BeautifulSoup(html, "html.parser")

        flood_section = cls._find_status_section(
            soup, "Flood Status"
        )
        low_water_section = cls._find_status_section(
            soup, "Low Water Status"
        )

        data: dict[str, str] = {}

        for river_key, display_name in RIVERS:
            data[f"{TYPE_FLOOD}_{river_key}"] = cls._extract_status(
                flood_section,
                display_name,
                FLOOD_STATUSES,
            )
            data[f"{TYPE_LOW_WATER}_{river_key}"] = cls._extract_status(
                low_water_section,
                display_name,
                LOW_WATER_STATUSES,
            )

        return data

    @classmethod
    def _parse_dashboard(cls, html: str) -> dict[str, str]:
        """Parse flood and low-water statuses from dashboard text."""
        if not html or not html.strip():
            raise ValueError("The MVCA dashboard response was empty")

        soup = BeautifulSoup(html, "html.parser")
        page_text = cls._normalise(soup.get_text(" ", strip=True))
        folded = page_text.casefold()

        flood_label = "Flood Status"
        low_water_label = "Low Water Status"

        flood_start = folded.find(flood_label.casefold())
        low_water_start = folded.find(low_water_label.casefold())

        if flood_start < 0:
            raise ValueError("Could not find Flood Status in dashboard text")
        if low_water_start < 0:
            raise ValueError("Could not find Low Water Status in dashboard text")
        if low_water_start <= flood_start:
            raise ValueError("Unexpected order of MVCA status labels")

        flood_text = page_text[
            flood_start + len(flood_label):low_water_start
        ]
        low_water_text = page_text[
            low_water_start + len(low_water_label):
        ]

        data: dict[str, str] = {}

        for river_key, river_name in RIVERS:
            data[f"{TYPE_FLOOD}_{river_key}"] = cls._extract_text_status(
                flood_text, river_name, FLOOD_STATUSES
            )
            data[f"{TYPE_LOW_WATER}_{river_key}"] = cls._extract_text_status(
                low_water_text, river_name, LOW_WATER_STATUSES
            )

        return data

    @classmethod
    def _extract_text_status(
        cls,
        section_text: str,
        river: str,
        valid_statuses: tuple[str, ...],
    ) -> str:
        """Extract a status following a river name in a text section."""
        folded = section_text.casefold()
        river_start = folded.find(river.casefold())

        if river_start < 0:
            raise ValueError(f"Could not find '{river}' in status text")

        start = river_start + len(river)
        next_river_positions = [
            pos
            for _, name in RIVERS
            if name.casefold() != river.casefold()
            and (pos := folded.find(name.casefold(), start)) >= 0
        ]
        end = min(next_river_positions, default=len(section_text))
        river_status_text = section_text[start:end]

        for status in sorted(valid_statuses, key=len, reverse=True):
            if re.search(
                rf"(?<!\w){re.escape(status)}(?!\w)",
                river_status_text,
                re.IGNORECASE,
            ):
                return status

        raise ValueError(
            f"Could not identify a known status for '{river}'"
        )

    @staticmethod
    def _normalise(value: str) -> str:
        """Normalise whitespace in scraped text."""
        return re.sub(r"\s+", " ", value).strip()