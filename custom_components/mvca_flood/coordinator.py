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
    def _find_status_section(
        cls,
        soup: BeautifulSoup,
        heading_text: str,
    ):
        """Find the smallest ancestor containing a heading and all rivers."""
        heading = soup.find(
            lambda tag: (
                tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}
                and cls._normalise(tag.get_text(" ", strip=True)).casefold()
                == heading_text.casefold()
            )
        )

        if heading is None:
            raise ValueError(
                f"Could not find the '{heading_text}' heading"
            )

        container = heading.parent

        while container is not None:
            text = cls._normalise(
                container.get_text(" ", strip=True)
            )
            if all(name in text for _, name in RIVERS):
                return container

            container = container.parent

        raise ValueError(
            f"Could not find all river data under '{heading_text}'"
        )

    @classmethod
    def _extract_status(
        cls,
        section,
        river: str,
        valid_statuses: tuple[str, ...],
    ) -> str:
        """Extract a known status associated with a river."""
        river_element = section.find(
            string=lambda value: (
                value is not None
                and river.casefold() in cls._normalise(value).casefold()
            )
        )

        if river_element is None:
            raise ValueError(
                f"Could not find '{river}' in the status section"
            )

        # Search nearby elements first, avoiding unrelated page content.
        element = river_element.parent

        for _ in range(5):
            if element is None:
                break

            text = cls._normalise(element.get_text(" ", strip=True))

            for status in sorted(
                valid_statuses,
                key=len,
                reverse=True,
            ):
                if status.casefold() in text.casefold():
                    return status

            element = element.parent

        raise ValueError(
            f"Could not identify a known status for '{river}'. "
            "The MVCA page may have changed or published a new status."
        )

    @staticmethod
    def _normalise(value: str) -> str:
        """Normalise whitespace in scraped text."""
        return re.sub(r"\s+", " ", value).strip()