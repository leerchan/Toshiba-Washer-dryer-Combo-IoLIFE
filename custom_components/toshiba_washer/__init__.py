"""Toshiba IoLIFE washer (TW-127XP2R) over the LAN, via stock midea-local."""

from collections.abc import Mapping
from typing import Any

from midealocal.const import ProtocolVersion

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .washer import ToshibaWasher

DOMAIN = "toshiba_washer"
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]
WASHER_TYPE = 0xDB
LAN_PORT = 6444

type WasherConfigEntry = ConfigEntry[ToshibaWasher]


def create_device(data: Mapping[str, Any]) -> ToshibaWasher:
    """Build the washer device for the stored entry data."""
    return ToshibaWasher(
        name=data["name"],
        device_id=data["device_id"],
        ip_address=data["ip_address"],
        port=LAN_PORT,
        token=data["token"],
        key=data["key"],
        device_protocol=ProtocolVersion(data["protocol"]),
        model=data["model"],
        subtype=0,
        serial_number=data["sn"],
    )


async def async_setup_entry(hass: HomeAssistant, entry: WasherConfigEntry) -> bool:
    """Start talking to the washer."""
    device = create_device(entry.data)
    # ponytail: no connect check here; the device's own supervisor keeps
    # reconnecting while the washer sleeps, entities show unavailable meanwhile
    await device.open()
    entry.runtime_data = device
    entry.async_on_unload(device.close)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WasherConfigEntry) -> bool:
    """Unload the entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
