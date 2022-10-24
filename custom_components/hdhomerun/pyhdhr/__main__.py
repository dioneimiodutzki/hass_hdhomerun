"""Basic CLI for testing pyhdr."""

# region #-- imports --#
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Tuple

import asyncclick as click

from .discover import Discover, DiscoverMode, HDHomeRunDevice
from .logger import Logger

# endregion

_LOGGER = logging.getLogger(__name__)
log_formatter: Logger = Logger()

click.anyio_backend = "asyncio"


@click.group(invoke_without_command=True)
@click.option("-v", "--verbose", count=True)
@click.pass_context
async def cli(ctx: click.Context = None, verbose: int = 0) -> None:
    """Initialise the CLI."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
    else:
        if verbose:
            logging.basicConfig()
            _LOGGER.setLevel(logging.DEBUG)
            if verbose > 1:
                logging.getLogger("pyhdhr").setLevel(logging.DEBUG)

    await asyncio.sleep(0.1)


@cli.command()
@click.option("-b", "--broadcast-address", default="255.255.255.255")
@click.option("-m", "--mode", default=DiscoverMode.AUTO.value)
async def discover(
    broadcast_address: str | None = None,
    mode: DiscoverMode = DiscoverMode.AUTO,
) -> None:
    """Attempt to discover devices."""
    _LOGGER.debug(log_formatter.format("entered, args: %s"), locals())

    devices: List[HDHomeRunDevice] = await Discover(
        broadcast_address=broadcast_address, mode=mode
    ).async_discover()

    dev: HDHomeRunDevice
    for dev in devices:
        await dev.async_gather_details()
        await dev.async_refresh_tuner_status()
        _display_data(
            _build_display_data(
                mappings=[
                    ("device_id", "Device ID"),
                    ("device_type", "Device Type"),
                    ("discovery_method", "Discovery Method"),
                    ("device_auth_string", "Device Auth"),
                    ("base_url", "Base URL"),
                    ("lineup_url", "LineUp URL"),
                    ("tuner_count", "# Tuners"),
                    ("model", "Model"),
                    ("hw_model", "HW Model"),
                    ("installed_version", "Firmware Version"),
                    ("latest_version", "Latest Firmware Version"),
                    ("channel_scanning", "Channel Scanning"),
                    ("tuner_status", "Tuner Status"),
                    # (
                    #     "channels",
                    #     "Channels",
                    #     "\n  "
                    #     + "\n  ".join(
                    #         [
                    #             f"{channel.get('GuideNumber')}: {channel.get('GuideName')}"
                    #             for channel in dev.channels
                    #         ]
                    #     ),
                    # ),
                ],
                obj=dev,
                title=dev.friendly_name or dev.device_id,
            )
        )

    _LOGGER.debug(log_formatter.format("exited"))


@cli.command()
@click.option("--target", required=True)
async def restart(target: str) -> None:
    """Issue a restart command to the device."""
    _LOGGER.debug(log_formatter.format("entered, args: %s"), locals())

    device: HDHomeRunDevice = HDHomeRunDevice(host=target)
    await device.async_restart()

    _LOGGER.debug(log_formatter.format("exited"))


@cli.command()
@click.option("--target", required=True)
@click.option("--variable", required=True)
async def get_variable(target: str, variable: str) -> None:
    """Retrieve a specific variable from the device."""
    _LOGGER.debug(log_formatter.format("entered, args: %s"), locals())

    device: HDHomeRunDevice = HDHomeRunDevice(host=target)
    ret = await device.async_get_protocol_variable(name=variable)

    click.echo(ret)

    _LOGGER.debug(log_formatter.format("exited"))


def _build_display_data(
    mappings: List[Tuple],
    obj: HDHomeRunDevice | Dict,
    indent: int = 0,
    title: str = "",
):
    """Build the string to display the given data."""
    ret: str = ""
    if title:
        ret = f"{title}\n"
        ret += f"{len(title) * '-'}\n"

    for properties in mappings:
        try:
            property_name, display_name, display_value = properties
        except ValueError:
            display_value = None
            property_name, display_name = properties

        if display_value is None:
            if isinstance(obj, Dict):
                display_value = obj.get(property_name)
            else:
                display_value = getattr(obj, property_name, None)

        ret += f"{indent * ' '}{display_name}: {display_value}\n"

    return ret.rstrip()


def _display_data(message: str = "") -> None:
    """Display the given data on screen."""
    click.echo(message)


if __name__ == "__main__":
    cli()
