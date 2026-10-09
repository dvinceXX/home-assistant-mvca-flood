"""MVCA Flood & Low Water sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory
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


@dataclass(frozen=True, kw_only=True)
class MVCASensorDescription(SensorEntityDescription):
    """Describe an MVCA sensor."""

    key: str
    status_type: str
    river: str


SENSORS: Final[tuple[MVCASensorDescription, ...]] = (
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
    def native_value(self) -> str | None:
        """Return the current status."""
        if self.coordinator.data is None:
            return None

        return self.coordinator.data.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return additional attributes."""
        return {"source": DASHBOARD_URL}