"""Data coordinator for MVCA Flood & Low Water."""

from __future__ import annotations

from datetime import timedelta
import logging
import re

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_SCAN_INTERVAL,
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

type MVCAConfigEntry = ConfigEntry[MVCADataUpdateCoordinator]


class MVCADataUpdateCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Coordinate MVCA data updates."""

    config_entry: MVCAConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: MVCAConfigEntry,
    ) -> None:
        """Initialize the coordinator."""

        scan_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(minutes=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, str]:
        """Fetch and parse MVCA status data."""

        session = async_get_clientsession(self.hass)

        try:
            async with session.get(
                DASHBOARD_URL,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                html = await response.text()

            return self._parse_dashboard(html)

        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Unable to retrieve MVCA data: {err}") from err

        except ValueError as err:
            raise UpdateFailed(f"Unable to parse MVCA data: {err}") from err

    @staticmethod
    def _normalise(value: str) -> str:
        """Normalise whitespace in scraped text."""

        return re.sub(r"\s+", " ", value).strip()

@classmethod
def _parse_dashboard(cls, html: str) -> dict[str, str]:
    """Parse MVCA dashboard HTML."""
    soup = BeautifulSoup(html, "html.parser")

    flood_section = cls._find_status_section(soup, "Flood Status")
    low_water_section = cls._find_status_section(soup, "Low Water Status")

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
def _find_status_section(
    soup: BeautifulSoup,
    heading_text: str,
):
    """Find the DOM section containing a status heading."""
    heading = soup.find(
        lambda tag: (
            tag.name in {"h2", "h3", "h4"}
            and tag.get_text(" ", strip=True).lower()
            == heading_text.lower()
        )
    )

    if heading is None:
        raise ValueError(f"Could not find '{heading_text}' section")

    # Walk up until we find a container that contains the status
    # heading and its associated river/status elements.
    container = heading.parent

    while container is not None:
        text = container.get_text(" ", strip=True)

        if (
            "Mississippi River" in text
            and "Carp River" in text
            and "Lower Ottawa" in text
        ):
            return container

        container = container.parent

    raise ValueError(f"Could not find data for '{heading_text}'")


@classmethod
def _extract_status(cls, section, river: str) -> str:
    """Extract the status associated with a river."""
    valid_statuses = (
        "Normal",
        "Watershed Conditions Statement - Water Safety",
        "Watershed Conditions Statement - Flood Outlook",
        "Flood Watch",
        "Flood Warning",
    )

    # Find the element containing the river name.
    river_element = section.find(
        string=lambda value: value and river in value
    )

    if river_element is None:
        raise ValueError(f"Could not find '{river}' in MVCA section")

    # Inspect the closest small container first.
    element = river_element.parent

    for _ in range(4):
        if element is None:
            break

        text = cls._normalise(element.get_text(" ", strip=True))

        # The status should be one of the known MVCA values.
        for status in valid_statuses:
            if status in text:
                return status

        element = element.parent

    raise ValueError(
        f"Could not find valid status for '{river}'"
    )