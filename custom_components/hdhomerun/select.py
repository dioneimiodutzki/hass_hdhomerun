"""Select entity."""

# region #-- imports --#
from __future__ import annotations

import dataclasses
from typing import Any, Callable, List

from homeassistant.components.select import DOMAIN as ENTITY_DOMAIN
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import HDHomerunEntity
from .const import (
    CONF_DATA_COORDINATOR_GENERAL,
    DOMAIN,
    SIGNAL_HDHOMERUN_CHANNEL_SOURCE_CHANGE,
)

# endregion


# region #-- select entity descriptions --#
@dataclasses.dataclass
class OptionalHDHomeRunSelectDescription:
    """Represent the optional attributes of the select description."""

    extra_attributes_args: dict | None = dataclasses.field(default_factory=dict)
    extra_attributes: Callable[[Any], dict] | None = None
    options: Callable[[Any], list[str]] | list[str] = dataclasses.field(
        default_factory=list
    )


@dataclasses.dataclass
class RequiredHDHomeRunSelectDescription:
    """Represent the required attributes of the select description."""


@dataclasses.dataclass
class HDHomeRunSelectDescription(
    OptionalHDHomeRunSelectDescription,
    SelectEntityDescription,
    RequiredHDHomeRunSelectDescription,
):
    """Describes select entity."""


# endregion


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][
        CONF_DATA_COORDINATOR_GENERAL
    ]

    selects: List[HDHomeRunSelect] = [
        HDHomeRunSelect(
            config_entry=config_entry,
            coordinator=coordinator,
            description=HDHomeRunSelectDescription(
                key="channel_sources",
                name="Channel Sources",
            ),
            hass=hass,
        )
    ]

    async_add_entities(selects)


class HDHomeRunSelect(HDHomerunEntity, SelectEntity):
    """Representation for a select entity."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
        description: HDHomeRunSelectDescription,
        hass: HomeAssistant,
    ) -> None:
        """Initialise."""
        self._attr_current_option = None
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False
        self.entity_domain = ENTITY_DOMAIN

        super().__init__(
            config_entry=config_entry,
            coordinator=coordinator,
            description=description,
            hass=hass,
        )

    async def async_select_option(self, option: str) -> None:
        """Select the option."""
        self._attr_current_option = option
        await self.async_update_ha_state()
        async_dispatcher_send(
            self.hass,
            SIGNAL_HDHOMERUN_CHANNEL_SOURCE_CHANGE,
            self._attr_current_option,
        )

    @property
    def options(self) -> List[str] | None:
        """Build the options for the select."""
        if self.entity_description.key:
            return getattr(self.coordinator.data, self.entity_description.key, None)

        if isinstance(self.entity_description.options, Callable):
            return self.entity_description.options(self.coordinator.data)

        return self.entity_description.options
