"""Data coordinator for MVCA Flood & Low Water."""

from __future__ import annotations

from datetime import timedelta
import logging
import re

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DASHBOARD_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    RIVER_CARP,
    RIVER_LOWER_OTTAWA,
    RIVER_MISSISSIPPI,
    TYPE_FLOOD,
    TYPE_LOW_WATER,
)

_LOGGER = logging.getLogger(__name__)


class MVCADataUpdateCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Coordinate MVCA data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""

        scan_interval = config_entry.options.get(
            "scan_interval",
            DEFAULT_SCAN_INTERVAL,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(minutes=scan_interval),
        )

        self._session: aiohttp.ClientSession | None = None

    async def _async_update_data(self) -> dict[str, str]:
        """Fetch and parse MVCA status data."""

        try:
            if self._session is None:
                self._session = aiohttp.ClientSession()

            timeout = aiohttp.ClientTimeout(total=30)

            async with self._session.get(
                DASHBOARD_URL,
                timeout=timeout,
                headers={
                    "User-Agent": (
                        "Home Assistant MVCA Flood Integration"
                    )
                },
            ) as response:
                response.raise_for_status()
                html = await response.text()

            return self._parse_dashboard(html)

        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(
                f"Unable to retrieve MVCA data: {err}"
            ) from err

        except ValueError as err:
            raise UpdateFailed(
                f"Unable to parse MVCA data: {err}"
            ) from err

    @staticmethod
    def _normalise(value: str) -> str:
        """Normalise whitespace in scraped text."""

        return re.sub(r"\s+", " ", value).strip()

    @classmethod
    def _parse_dashboard(
        cls,
        html: str,
    ) -> dict[str, str]:
        """Parse MVCA dashboard HTML."""

        soup = BeautifulSoup(html, "html.parser")

        text = cls._normalise(soup.get_text(" ", strip=True))

        # The dashboard currently presents the data in this form:
        #
        # Flood Status
        # Mississippi River Normal
        # Carp River Normal
        # Lower Ottawa Normal
        #
        # Low Water Status
        # Mississippi River Normal
        # Carp River Normal
        # Lower Ottawa Normal
        #
        # We deliberately parse the labelled sections instead of relying
        # on arbitrary DOM indexes.

        flood_section = cls._extract_section(
            text,
            "Flood Status",
            "Low Water Status",
        )

        low_water_section = cls._extract_section(
            text,
            "Low Water Status",
            "Normal status indicates",
        )

        data: dict[str, str] = {}

        for river, display_name in (
            (RIVER_MISSISSIPPI, "Mississippi River"),
            (RIVER_CARP, "Carp River"),
            (RIVER_LOWER_OTTAWA, "Lower Ottawa"),
        ):
            data[f"{TYPE_FLOOD}_{river}"] = cls._extract_status(
                flood_section,
                display_name,
            )

            data[f"{TYPE_LOW_WATER}_{river}"] = cls._extract_status(
                low_water_section,
                display_name,
            )

        return data

    @staticmethod
    def _extract_section(
        text: str,
        start: str,
        end: str,
    ) -> str:
        """Extract text between two headings."""

        start_index = text.find(start)

        if start_index == -1:
            raise ValueError(f"Could not find '{start}' section")

        start_index += len(start)

        end_index = text.find(end, start_index)

        if end_index == -1:
            section = text[start_index:]
        else:
            section = text[start_index:end_index]

        return section.strip()

    @classmethod
    def _extract_status(
        cls,
        section: str,
        river: str,
    ) -> str:
        """Extract the status associated with a river."""

        position = section.find(river)

        if position == -1:
            raise ValueError(
                f"Could not find '{river}' in MVCA section"
            )

        remainder = section[position + len(river):]

        # Status ends at the next known river name.
        next_positions = [
            position
            for position in (
                remainder.find("Mississippi River"),
                remainder.find("Carp River"),
                remainder.find("Lower Ottawa"),
            )
            if position >= 0
        ]

        if next_positions:
            remainder = remainder[: min(next_positions)]

        value = cls._normalise(remainder)

        # The dashboard should give us a short status. Protect against
        # accidentally returning unrelated page content.
        if not value or len(value) > 100:
            raise ValueError(
                f"Invalid status for '{river}': {value!r}"
            )

        return value