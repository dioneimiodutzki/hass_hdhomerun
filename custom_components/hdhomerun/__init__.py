""""""

# region #-- imports --#
import logging
from datetime import timedelta
from typing import (
    List,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_DATA_COORDINATOR_GENERAL,
    CONF_DATA_COORDINATOR_TUNER_STATUS,
    CONF_SCAN_INTERVAL_TUNER_STATUS,
    CONF_HOST,
    DEF_SCAN_INTERVAL_SECS,
    DEF_SCAN_INTERVAL_TUNER_STATUS_SECS,
    DOMAIN,
    PLATFORMS,
)
from .hdhomerun import (
    DEF_DISCOVER,
    HDHomeRunDevice,
    HDHomeRunExceptionOldFirmware,
)
from .logger import HDHomerunLogger

# endregion

_LOGGER = logging.getLogger(__name__)


async def _async_reload(hass: HomeAssistant, config_entry: ConfigEntry):
    """Reload the config entry

    :param hass:
    :param config_entry:
    :return:
    """

    return await hass.config_entries.async_reload(config_entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Setup a config entry"""

    tuner_coordinator: bool = True
    log_formatter = HDHomerunLogger(unique_id=config_entry.unique_id)
    _LOGGER.debug(log_formatter.message_format("entered"))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(config_entry.entry_id, {})

    # listen for options updates
    config_entry.async_on_unload(
        config_entry.add_update_listener(_async_reload)
    )

    hdhomerun_device = HDHomeRunDevice(
        host=config_entry.data.get(CONF_HOST),
        loop=hass.loop,
        session=async_get_clientsession(hass=hass),
    )
    try:
        await hdhomerun_device.get_details(
            include_discover=True,
            include_tuner_status=True,
        )
    except HDHomeRunExceptionOldFirmware as err:
        _LOGGER.warning(log_formatter.message_format("%s"), err)
        tuner_coordinator = False
    except Exception as err:
        raise ConfigEntryNotReady from err

    # region #-- set up the coordinators --#
    async def _async_data_coordinator_update() -> HDHomeRunDevice:
        """"""

        try:
            await hdhomerun_device.get_details(
                include_discover=True,
                include_lineups=True,
            )
        except HDHomeRunExceptionOldFirmware as exc:
            _LOGGER.warning(log_formatter.message_format("%s"), exc)

        return hdhomerun_device

    async def _async_data_coordinator_tuner_status_update() -> HDHomeRunDevice:
        """"""

        try:
            await hdhomerun_device.get_details(
                include_tuner_status=True,
            )
        except HDHomeRunExceptionOldFirmware as exc:
            _LOGGER.warning(log_formatter.message_format("%s"), exc)

        return hdhomerun_device

    coordinator_general: DataUpdateCoordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_general",
        update_method=_async_data_coordinator_update,
        update_interval=timedelta(seconds=config_entry.options.get(CONF_SCAN_INTERVAL, DEF_SCAN_INTERVAL_SECS)),
    )
    hass.data[DOMAIN][config_entry.entry_id][CONF_DATA_COORDINATOR_GENERAL] = coordinator_general
    await coordinator_general.async_config_entry_first_refresh()

    if tuner_coordinator:
        coordinator_tuner_status: DataUpdateCoordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_tuner_status",
            update_method=_async_data_coordinator_tuner_status_update,
            update_interval=timedelta(
                seconds=config_entry.options.get(CONF_SCAN_INTERVAL_TUNER_STATUS, DEF_SCAN_INTERVAL_TUNER_STATUS_SECS)
            ),
        )
        hass.data[DOMAIN][config_entry.entry_id][CONF_DATA_COORDINATOR_TUNER_STATUS] = coordinator_tuner_status
        await coordinator_tuner_status.async_config_entry_first_refresh()
    # endregion

    # region #-- setup the platforms --#
    setup_platforms: List[str] = list(filter(None, PLATFORMS))
    _LOGGER.debug(log_formatter.message_format("setting up platforms: %s"), setup_platforms)
    hass.config_entries.async_setup_platforms(config_entry, setup_platforms)
    # endregion

    _LOGGER.debug(log_formatter.message_format("exited"))
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Cleanup when unloading a config entry"""

    # region #-- clean up the platforms --#
    setup_platforms: List[str] = list(filter(None, PLATFORMS))
    ret = await hass.config_entries.async_unload_platforms(config_entry, setup_platforms)
    if ret:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        ret = True
    else:
        ret = False
    # endregion

    return ret
