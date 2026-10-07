"""Data coordinator for MVCA Flood & Low Water."""

from __future__ import annotations

from datetime import timedelta
import re
from typing import Any

from bs4 import BeautifulSoup
from aiohttp import ClientError, ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DASHBOARD_URL,
    DEFAULT_SCAN_INTERVAL,
    RIVER_CARP,
    RIVER_LOWER_OTTAWA,
    RIVER_MISSISSIPPI,
    TYPE_FLOOD,
    TYPE_LOW_WATER,
)


class MVCADataUpdateCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Coordinate MVCA data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass

        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
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
                f"Unable to retrieve MVCA data: {err}"
            ) from err

        try:
            return self._parse_dashboard(html)
        except (ValueError, AttributeError) as err:
            raise UpdateFailed(
                f"Unable to parse MVCA data: {err}"
            ) from err

    @classmethod
    def _parse_dashboard(cls, html: str) -> dict[str, str]:
        """Parse MVCA dashboard HTML."""
        soup = BeautifulSoup(html, "html.parser")

        flood_section = cls._find_status_section(
            soup,
            "Flood Status",
        )

        low_water_section = cls._find_status_section(
            soup,
            "Low Water Status",
        )

        data: dict[str, str] = {}

        rivers = (
            (RIVER_MISSISSIPPI, "Mississippi River"),
            (RIVER_CARP, "Carp River"),
            (RIVER_LOWER_OTTAWA, "Lower Ottawa"),
        )

        for river, display_name in rivers:
            data[f"{TYPE_FLOOD}_{river}"] = cls._extract_status(
                flood_section,
                display_name,
            )

            data[f"{TYPE_LOW_WATER}_{river}"] = cls._extract_status(
                low_water_section,
                display_name,
            )

        return data

    @classmethod
    def _find_status_section(
        cls,
        soup: BeautifulSoup,
        heading_text: str,
    ) -> Any:
        """Find the DOM section containing a status heading."""
        heading = soup.find(
            lambda tag: (
                tag.name in {"h2", "h3", "h4"}
                and cls._normalise(tag.get_text(" ", strip=True)).lower()
                == heading_text.lower()
            )
        )

        if heading is None:
            raise ValueError(
                f"Could not find '{heading_text}' section"
            )

        # Start with the heading's parent and walk upward until the
        # container contains all three river names.
        container = heading.parent

        while container is not None:
            text = cls._normalise(
                container.get_text(" ", strip=True)
            )

            if (
                "Mississippi River" in text
                and "Carp River" in text
                and "Lower Ottawa" in text
            ):
                return container

            container = container.parent

        raise ValueError(
            f"Could not find data for '{heading_text}'"
        )

    @classmethod
    def _extract_status(
        cls,
        section: Any,
        river: str,
    ) -> str:
        """Extract the status associated with a river."""
        valid_statuses = (
            "Normal",
            "Watershed Conditions Statement - Water Safety",
            "Watershed Conditions Statement - Flood Outlook",
            "Flood Watch",
            "Flood Warning",
        )

        # Find the text node containing the river name.
        river_element = section.find(
            string=lambda value: (
                value is not None and river in value
            )
        )

        if river_element is None:
            raise ValueError(
                f"Could not find '{river}' in MVCA section"
            )

        # The status should be located in the same small DOM
        # container as the river name. Avoid parsing the entire
        # page or section, which can accidentally consume MVCA's
        # navigation menu.
        element = river_element.parent

        for _ in range(5):
            if element is None:
                break

            text = cls._normalise(
                element.get_text(" ", strip=True)
            )

            # Prefer the longest statuses first so that
            # "Water Safety" / "Flood Outlook" are not accidentally
            # matched incorrectly.
            for status in sorted(
                valid_statuses,
                key=len,
                reverse=True,
            ):
                if status in text:
                    return status

            element = element.parent

        raise ValueError(
            f"Could not find valid status for '{river}'"
        )

    @staticmethod
    def _normalise(value: str) -> str:
        """Normalise whitespace in scraped text."""
        return re.sub(r"\s+", " ", value).strip()