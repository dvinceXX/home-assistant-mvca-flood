"""MVCA Flood & Low Water sensors."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DASHBOARD_URL,
    DOMAIN,
    RIVER_CARP,
    RIVER_LOWER_OTTAWA,
    RIVER_MISSISSIPPI,
    TYPE_FLOOD,
    TYPE_LOW_WATER,
)
from .coordinator import MVCAConfigEntry, MVCADataUpdateCoordinator


# These are ordinal severity values for automations, not official MVCA codes.
FLOOD_STATUS_VALUES: Final[dict[str, int]] = {
    "Normal": 0,
    "Watershed Conditions Statement - Water Safety": 1,
    "Watershed Conditions Statement - Flood Outlook": 2,
    "Flood Watch": 3,
    "Flood Warning": 4,
}
LOW_WATER_STATUS_VALUES: Final[dict[str, int]] = {
    "Normal": 0,
    "Level I": 1,
    "Level II": 2,
    "Level III": 3,
}


@dataclass(frozen=True, kw_only=True)
class MVCASensorDescription(SensorEntityDescription):
    """Describe an MVCA sensor."""

    key: str
    status_type: str
    river: str
    is_numeric: bool = False


TEXT_SENSORS: Final[tuple[MVCASensorDescription, ...]] = (
    MVCASensorDescription(
        key=f"{TYPE_FLOOD}_{RIVER_MISSISSIPPI}",
        name="Mississippi River Flood Status",
        icon="mdi:home-flood",
        status_type=TYPE_FLOOD,
        river=RIVER_MISSISSIPPI,
    ),
    MVCASensorDescription(
        key=f"{TYPE_FLOOD}_{RIVER_CARP}",
        name="Carp River Flood Status",
        icon="mdi:home-flood",
        status_type=TYPE_FLOOD,
        river=RIVER_CARP,
    ),
    MVCASensorDescription(
        key=f"{TYPE_FLOOD}_{RIVER_LOWER_OTTAWA}",
        name="Lower Ottawa Flood Status",
        icon="mdi:home-flood",
        status_type=TYPE_FLOOD,
        river=RIVER_LOWER_OTTAWA,
    ),
    MVCASensorDescription(
        key=f"{TYPE_LOW_WATER}_{RIVER_MISSISSIPPI}",
        name="Mississippi River Low Water Status",
        icon="mdi:water-minus",
        status_type=TYPE_LOW_WATER,
        river=RIVER_MISSISSIPPI,
    ),
    MVCASensorDescription(
        key=f"{TYPE_LOW_WATER}_{RIVER_CARP}",
        name="Carp River Low Water Status",
        icon="mdi:water-minus",
        status_type=TYPE_LOW_WATER,
        river=RIVER_CARP,
    ),
    MVCASensorDescription(
        key=f"{TYPE_LOW_WATER}_{RIVER_LOWER_OTTAWA}",
        name="Lower Ottawa Low Water Status",
        icon="mdi:water-minus",
        status_type=TYPE_LOW_WATER,
        river=RIVER_LOWER_OTTAWA,
    ),
)

NUMERIC_SENSORS: Final[tuple[MVCASensorDescription, ...]] = tuple(
    replace(
        description,
        key=f"{description.key}_numeric",
        name=f"{description.name} Numeric",
        icon="mdi:numeric",
        is_numeric=True,
    )
    for description in TEXT_SENSORS
)

SENSORS: Final[tuple[MVCASensorDescription, ...]] = (
    *TEXT_SENSORS,
    *NUMERIC_SENSORS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MVCAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MVCA sensors."""
    coordinator: MVCADataUpdateCoordinator = entry.runtime_data

    async_add_entities(
        MVCASensor(coordinator, description)
        for description in SENSORS
    )


class MVCASensor(
    CoordinatorEntity[MVCADataUpdateCoordinator],
    SensorEntity,
):
    """Representation of an MVCA sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MVCADataUpdateCoordinator,
        description: MVCASensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, context=description.key)

        self.entity_description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_unique_id = f"mvca_{description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "mvca")},
            name="MVCA Flood & Low Water",
            manufacturer="Mississippi Valley Conservation Authority",
            configuration_url=DASHBOARD_URL,
        )

    @property
    def native_value(self) -> str | int | None:
        """Return the text status or its numeric severity value."""
        if self.coordinator.data is None:
            return None

        status = self.coordinator.data.get(self.entity_description.key)
        if status is None:
            # Numeric sensor keys have a _numeric suffix; use the original
            # text status key to look up the corresponding status.
            if self.entity_description.is_numeric:
                status_key = self.entity_description.key.removesuffix("_numeric")
                status = self.coordinator.data.get(status_key)
            if status is None:
                return None

        if not self.entity_description.is_numeric:
            return status

        mapping = (
            FLOOD_STATUS_VALUES
            if self.entity_description.status_type == TYPE_FLOOD
            else LOW_WATER_STATUS_VALUES
        )
        # Do not turn unrecognized statuses into a misleading numeric zero.
        return mapping.get(status)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return additional attributes."""
        return {"source": DASHBOARD_URL}
