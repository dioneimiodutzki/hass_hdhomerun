"""Sensors."""

# region #-- imports --#
from __future__ import annotations

import dataclasses
import logging
import os.path
import re
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Mapping, Optional

from homeassistant.components.sensor import DOMAIN as ENTITY_DOMAIN
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    StateType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import HDHomerunEntity, entity_cleanup
from .const import (
    CONF_DATA_COORDINATOR_GENERAL,
    CONF_DATA_COORDINATOR_TUNER_STATUS,
    CONF_TUNER_CHANNEL_ENTITY_PICTURE_PATH,
    CONF_TUNER_CHANNEL_FORMAT,
    CONF_TUNER_CHANNEL_NAME,
    CONF_TUNER_CHANNEL_NUMBER,
    CONF_TUNER_CHANNEL_NUMBER_NAME,
    DEF_TUNER_CHANNEL_ENTITY_PICTURE_PATH,
    DEF_TUNER_CHANNEL_FORMAT,
    DOMAIN,
    UPDATE_DOMAIN,
)
from .pyhdhr.const import DiscoverMode
from .pyhdhr.discover import HDHomeRunDevice

# endregion

_LOGGER = logging.getLogger(__name__)


# region #-- sensor descriptions --#
@dataclasses.dataclass(frozen=True)
class AdditionalSensorDescription:
    """Represent additional options for the button entity."""

    extra_attributes: Callable | None = None
    state_value: Optional[Callable[[Any], Any]] = None


# endregion


STATE_IDLE = "idle"
STATE_IN_USE = "in_use"
STATE_SCANNING = "scanning"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the sensor."""
    coordinator_general: DataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ][CONF_DATA_COORDINATOR_GENERAL]
    coordinator_tuner: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        CONF_DATA_COORDINATOR_TUNER_STATUS
    ]

    sensors: List[HDHomerunSensor] = []
    sensors_to_remove: List[HDHomerunSensor] = []

    # region #-- add version sensors if need be --#
    if UPDATE_DOMAIN is None:
        sensors.extend(
            [
                HDHomerunSensor(
                    config_entry=config_entry,
                    coordinator=coordinator_general,
                    description=SensorEntityDescription(
                        key="current_firmware",
                        name="Version",
                    ),
                ),
                HDHomerunSensor(
                    additional_description=AdditionalSensorDescription(
                        state_value=lambda d: d.latest_firmware or d.current_firmware,
                    ),
                    config_entry=config_entry,
                    coordinator=coordinator_general,
                    description=SensorEntityDescription(
                        key="",
                        name="Newest Version",
                    ),
                ),
            ]
        )
    else:  # remove the existing version sensors if the update entity is available
        sensors_to_remove.extend(
            [
                HDHomerunSensor(
                    config_entry=config_entry,
                    coordinator=coordinator_general,
                    description=SensorEntityDescription(
                        key="current_firmware",
                        name="Version",
                    ),
                ),
                HDHomerunSensor(
                    config_entry=config_entry,
                    coordinator=coordinator_general,
                    description=SensorEntityDescription(
                        key="",
                        name="Newest Version",
                    ),
                ),
            ]
        )
    # endregion

    # region #-- add tuner sensors --#
    hdhomerun_device: HDHomeRunDevice | None = coordinator_tuner.data
    if hdhomerun_device is not None:
        for tuner in hdhomerun_device.tuner_status:
            sensors.append(
                HDHomerunTunerStatusSensor(
                    config_entry=config_entry,
                    coordinator=coordinator_tuner,
                    description=SensorEntityDescription(
                        key="",
                        name=tuner.get("Resource").title() + "_status",
                        translation_key="tuner_status",
                    ),
                )
            )

            sensors.append(
                HDHomerunTunerSignalSensor(
                    config_entry=config_entry,
                    coordinator=coordinator_tuner,
                    api_parameter="SignalQualityPercent",
                    description=SensorEntityDescription(
                        key="",
                        name=tuner.get("Resource").title() + "_signal_quality"
                    ),
                )
            )

            sensors.append(
                HDHomerunTunerSignalSensor(
                    config_entry=config_entry,
                    coordinator=coordinator_tuner,
                    api_parameter="SignalStrengthPercent",
                    description=SensorEntityDescription(
                        key="",
                        name=tuner.get("Resource").title() + "_signal_strength"
                    ),
                )
            )
    # endregion

    # region #-- add conditional sensors --#
    if coordinator_general.data.discovery_method is DiscoverMode.HTTP:
        sensors.extend(
            [
                HDHomerunSensor(
                    additional_description=AdditionalSensorDescription(
                        extra_attributes=lambda d: (
                            {
                                "channels": [
                                    channel.get("GuideName", None)
                                    for channel in d.channels
                                    if channel.get("Enabled", None) == 0
                                ]
                            }
                        ),
                        state_value=lambda d: len(
                            [
                                channel
                                for channel in d
                                if channel.get("Enabled", None) == 0
                            ]
                        ),
                    ),
                    config_entry=config_entry,
                    coordinator=coordinator_general,
                    description=SensorEntityDescription(
                        icon="mdi:playlist-remove",
                        key="channels",
                        name="Disabled Channels",
                        state_class=SensorStateClass.MEASUREMENT,
                        translation_key="disabled_channels",
                    ),
                ),
                HDHomerunSensor(
                    additional_description=AdditionalSensorDescription(
                        extra_attributes=lambda d: (
                            {
                                "channels": [
                                    channel.get("GuideName", None)
                                    for channel in d.channels
                                    if channel.get("Favorite", None) == 1
                                ]
                            }
                        ),
                        state_value=lambda d: len(
                            [
                                channel
                                for channel in d
                                if channel.get("Favorite", None) == 1
                            ]
                        ),
                    ),
                    config_entry=config_entry,
                    coordinator=coordinator_general,
                    description=SensorEntityDescription(
                        icon="mdi:playlist-star",
                        key="channels",
                        name="Favourite Channels",
                        state_class=SensorStateClass.MEASUREMENT,
                        translation_key="fav_channels",
                    ),
                ),
                HDHomerunSensor(
                    additional_description=AdditionalSensorDescription(
                        # pylint: disable=unnecessary-lambda
                        state_value=lambda d: len(d),
                    ),
                    config_entry=config_entry,
                    coordinator=coordinator_general,
                    description=SensorEntityDescription(
                        icon="mdi:text-long",
                        key="channels",
                        name="Channel Count",
                        state_class=SensorStateClass.MEASUREMENT,
                        translation_key="channel_count",
                    ),
                ),
            ]
        )
    # endregion

    # region #-- add default sensors --#
    sensors.extend(
        [
            HDHomerunSensor(
                config_entry=config_entry,
                coordinator=coordinator_general,
                description=SensorEntityDescription(
                    icon="mdi:transmission-tower-import",
                    key="tuner_count",
                    name="Tuner Count",
                    state_class=SensorStateClass.MEASUREMENT,
                    translation_key="tuner_count",
                ),
            )
        ]
    )
    # endregion

    async_add_entities(sensors)

    if sensors_to_remove:
        entity_cleanup(config_entry=config_entry, entities=sensors_to_remove, hass=hass)


# region #-- sensor classes --#
class HDHomerunSensor(HDHomerunEntity, SensorEntity):
    """Representation of an HDHomeRun sensor."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: DataUpdateCoordinator,
        description: SensorEntityDescription,
        additional_description: AdditionalSensorDescription | None = None,
    ) -> None:
        """Initialise."""
        self._additional_description: AdditionalSensorDescription | None = (
            additional_description
        )
        self.entity_domain = ENTITY_DOMAIN
        super().__init__(
            config_entry=config_entry,
            coordinator=coordinator,
            description=description,
        )

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> StateType | date | datetime:
        """Get the value of the sensor."""
        if self.coordinator.data:
            if (
                self._additional_description is not None
                and self._additional_description.state_value
            ):
                if self.entity_description.key:
                    return self._additional_description.state_value(
                        getattr(
                            self.coordinator.data, self.entity_description.key, None
                        )
                    )
                return self._additional_description.state_value(self.coordinator.data)
            return getattr(self.coordinator.data, self.entity_description.key, None)

        return None


class HDHomerunTunerStatusSensor(HDHomerunEntity, SensorEntity):
    """Representation of an HDHomeRun tuner status.""" 

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: DataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialise."""
        self.entity_domain = ENTITY_DOMAIN
        super().__init__(
            config_entry=config_entry,
            coordinator=coordinator,
            description=description,
        )

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._tuner: dict = self._get_tuner()

    def _get_tuner(self) -> Dict[str, int | str]:
        """Get the tuner information from the coordinator."""
        tuner: Dict[str, int | str] = {}
        for _tuner in self.coordinator.data.tuner_status:
            if (
                _tuner.get("Resource", "").lower()
                == self.entity_description.name.lower().split("_")[0]
            ):
                tuner = _tuner
                break

        return tuner

    def _handle_coordinator_update(self) -> None:
        """Update the device information when the coordinator updates."""
        super()._handle_coordinator_update()
        self._tuner = self._get_tuner()

    def _value(self) -> StateType | date | datetime:
        """Determine the value of the sensor."""
        ret = STATE_IDLE
        if self._tuner.get("VctNumber") and self._tuner.get("VctName"):
            channel_format = self._config.options.get(
                CONF_TUNER_CHANNEL_FORMAT, DEF_TUNER_CHANNEL_FORMAT
            )
            if channel_format == CONF_TUNER_CHANNEL_NAME:
                ret = self._tuner.get("VctName")
            elif channel_format == CONF_TUNER_CHANNEL_NUMBER:
                ret = self._tuner.get("VctNumber")
            elif channel_format == CONF_TUNER_CHANNEL_NUMBER_NAME:
                ret = f"{self._tuner.get('VctNumber')}: {self._tuner.get('VctName')}"
            else:
                ret = None
        elif self._tuner.get("TargetIP"):
            ret = STATE_IN_USE

        return ret

    @property
    def entity_picture(self) -> Optional[str]:
        """Get the entity picture based on configured paths."""
        ret = None
        entity_picture_path = self._config.options.get(
            CONF_TUNER_CHANNEL_ENTITY_PICTURE_PATH,
            DEF_TUNER_CHANNEL_ENTITY_PICTURE_PATH,
        )
        if entity_picture_path and self._value() not in (
            STATE_IDLE,
            STATE_IN_USE,
            STATE_SCANNING,
        ):
            ret = os.path.join(
                entity_picture_path, f"{self._tuner.get('VctName', '').lower()}.png"
            )

        return ret

    @property
    def extra_state_attributes(self) -> Optional[Mapping[str, Any]]:
        """Define additional information for the sensor."""
        regex = re.compile(r"(?<!^)(?=[A-Z])")
        ret = {
            regex.sub("_", k).lower().replace("_i_p", "_ip"): v
            for k, v in self._tuner.items()
            if k.lower() != "resource"
        }

        return ret

    @property
    def icon(self) -> Optional[str]:
        """Get the icon for the sensor."""
        ret = "mdi:television-classic"
        if self._value() in (STATE_IDLE, STATE_SCANNING):
            ret = "mdi:television-classic-off"

        return ret

    @property
    def native_value(self) -> StateType | date | datetime:
        """Get the value of the sensor."""
        return self._value()

class HDHomerunTunerSignalSensor(HDHomerunEntity, SensorEntity):
    """Representation of an HDHomeRun tuner signal parameters."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: DataUpdateCoordinator,
        api_parameter: api_parameter,
        description: SensorEntityDescription,
    ) -> None:
        """Initialise."""
        self.entity_domain = ENTITY_DOMAIN
        self.api_parameter = api_parameter
        super().__init__(
            config_entry=config_entry,
            coordinator=coordinator,
            description=description,
        )

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._tuner: dict = self._get_tuner()

    def _get_tuner(self) -> Dict[str, int | str]:
        """Get the tuner information from the coordinator."""
        tuner: Dict[str, int | str] = {}
        for _tuner in self.coordinator.data.tuner_status:
            if (
                _tuner.get("Resource", "").lower()
                == self.entity_description.name.lower().split("_")[0]
            ):
                tuner = _tuner
                break

        return tuner

    def _handle_coordinator_update(self) -> None:
        """Update the device information when the coordinator updates."""
        super()._handle_coordinator_update()
        self._tuner = self._get_tuner()

    def _value(self) -> StateType | date | datetime:
        """Determine the value of the sensor."""
        ret = None
        if self._tuner.get(self.api_parameter):
            ret = self._tuner.get(self.api_parameter)

        return ret

    @property
    def icon(self) -> Optional[str]:
        """Get the icon for the sensor."""
        ret = "mdi:signal"
        if self._value() == None:
            ret = "mdi:signal-off"

        return ret

    @property
    def native_value(self) -> StateType | date | datetime:
        """Get the value of the sensor."""
        return self._value()

# endregion
