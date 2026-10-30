"""Washer door and filter binary sensors."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WasherConfigEntry
from .sensor import WasherEntity
from .washer import ToshibaWasher


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WasherConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the washer binary sensors."""
    device = entry.runtime_data
    async_add_entities(
        [
            WasherBinarySensor(device, "door_open", BinarySensorDeviceClass.DOOR),
            WasherBinarySensor(device, "drain_filter_clean",
                               BinarySensorDeviceClass.PROBLEM),
            WasherBinarySensor(device, "dry_filter_clean",
                               BinarySensorDeviceClass.PROBLEM),
        ]
    )


class WasherBinarySensor(WasherEntity, BinarySensorEntity):
    """On/off device attribute."""

    def __init__(
        self,
        device: ToshibaWasher,
        key: str,
        device_class: BinarySensorDeviceClass,
    ) -> None:
        """Initialize."""
        super().__init__(device, key)
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        """Attribute value."""
        return self._device.attributes.get(self._key)
