""""""

# region #-- imports --#
import dataclasses
from typing import (
    Any,
    Callable,
    Optional,
)

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import slugify

from .const import (
    CONF_DATA_COORDINATOR_GENERAL,
    DOMAIN,
    ENTITY_SLUG,
)
from .entity_helpers import HDHomerunEntity
# endregion


# region #-- binary sensor descriptions --#
@dataclasses.dataclass
class OptionalHDHomerunBinarySensorDescription:
    """Represent the required attributes of the binary_sensor description."""

    state_value: Optional[Callable[[Any], bool]] = None


@dataclasses.dataclass
class RequiredHDHomerunBinarySensorDescription:
    """Represent the required attributes of the sensor description."""


@dataclasses.dataclass
class HDHomerunBinarySensorEntityDescription(
    OptionalHDHomerunBinarySensorDescription,
    BinarySensorEntityDescription,
    RequiredHDHomerunBinarySensorDescription,
):
    """Describes binary_sensor entity."""
# endregion


# region #-- binary sensor classes --#
class HDHomerunBinarySensor(HDHomerunEntity, BinarySensorEntity):
    """"""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: DataUpdateCoordinator,
        description: HDHomerunBinarySensorEntityDescription,
    ) -> None:
        """"""

        super().__init__(coordinator=coordinator, config_entry=config_entry)

        self.entity_description: HDHomerunBinarySensorEntityDescription = description

        self._attr_name = f"{ENTITY_SLUG} {config_entry.title.replace(ENTITY_SLUG, '')}: {self.entity_description.name}"
        self._attr_unique_id = f"{config_entry.unique_id}::binary_sensor::{slugify(self.entity_description.name)}"

    # region #-- properties --#
    @property
    def is_on(self) -> bool:
        """Return if the service is on."""

        if self._data:
            if self.entity_description.key:
                return self.entity_description.state_value(getattr(self._data, self.entity_description.key, None))
            else:
                return self.entity_description.state_value(self._data)
        else:
            return False
    # endregion
# endregion


BINARY_SENSORS: tuple[HDHomerunBinarySensorEntityDescription, ...] = (
    HDHomerunBinarySensorEntityDescription(
        key="",
        name="Update available",
        device_class=BinarySensorDeviceClass.UPDATE,
        state_value=lambda d: bool(d.latest_firmware),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor"""

    sensors = [
        HDHomerunBinarySensor(
            config_entry=config_entry,
            coordinator=hass.data[DOMAIN][config_entry.entry_id][CONF_DATA_COORDINATOR_GENERAL],
            description=description,
        )
        for description in BINARY_SENSORS
    ]

    async_add_entities(sensors, update_before_add=True)
