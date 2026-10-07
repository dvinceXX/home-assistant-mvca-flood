"""Constants for the MVCA Flood & Low Water integration."""

from __future__ import annotations

DOMAIN = "mvca_flood"

NAME = "MVCA Flood & Low Water"

DEFAULT_SCAN_INTERVAL = 30  # minutes

DASHBOARD_URL = "https://mvc.on.ca/engineering/water-management-dashboard/"

FLOOD_URL = "https://mvc.on.ca/flood-status/"
LOW_WATER_URL = "https://mvc.on.ca/low-water-status/"

CONF_SCAN_INTERVAL = "scan_interval"

RIVER_MISSISSIPPI = "mississippi_river"
RIVER_CARP = "carp_river"
RIVER_LOWER_OTTAWA = "lower_ottawa"

TYPE_FLOOD = "flood"
TYPE_LOW_WATER = "low_water"

FLOOD_STATUSES = (
    "Normal",
    "Watershed Conditions Statement - Water Safety",
    "Watershed Conditions Statement - Flood Outlook",
    "Flood Watch",
    "Flood Warning",
)

LOW_WATER_STATUSES = (
    "Normal",
    "Level I",
    "Level II",
    "Level III",
)