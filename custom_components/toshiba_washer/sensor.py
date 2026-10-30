"""Washer sensors."""

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import DOMAIN, WasherConfigEntry
from .washer import MODES, PROGRAMS, STAGES, ToshibaWasher

# midea-local DB status names used for Toshiba machine_status
STATUS_OPTIONS = ["idle", "standby", "start", "pause", "end"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WasherConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the washer sensors."""
    device = entry.runtime_data
    async_add_entities(
        [
            WasherSensor(device, "status", SensorDeviceClass.ENUM, STATUS_OPTIONS),
            WasherFinishTime(device),
            WasherSensor(device, "stage", SensorDeviceClass.ENUM,
                         [name for _, name in STAGES]),
            WasherSensor(device, "mode", SensorDeviceClass.ENUM, list(MODES.values())),
            WasherSensor(device, "program", SensorDeviceClass.ENUM,
                         list(PROGRAMS.values())),
            WasherSensor(device, "error_code", category=EntityCategory.DIAGNOSTIC),
        ]
    )


class WasherEntity(Entity):
    """Entity pushed by the midea-local device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: ToshibaWasher, key: str) -> None:
        """Initialize; names and states come from translations/<lang>.json."""
        self._device = device
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{device.device_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device.device_id))},
            manufacturer="Toshiba",
            model=str(device.model),
            name=device.name,
            serial_number=device.serial_number,
        )

    @property
    def available(self) -> bool:
        """Washer reachable on the LAN."""
        return bool(self._device.available)

    async def async_added_to_hass(self) -> None:
        """Follow device updates."""
        self._device.register_update(self._on_update)
        self.async_on_remove(lambda: self._device.unregister_update(self._on_update))

    @callback
    def _on_update(self, _status: dict[str, Any]) -> None:
        self.async_write_ha_state()


class WasherSensor(WasherEntity, SensorEntity):
    """Sensor showing one device attribute."""

    def __init__(
        self,
        device: ToshibaWasher,
        key: str,
        device_class: SensorDeviceClass | None = None,
        options: list[str] | None = None,
        category: EntityCategory | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(device, key)
        self._attr_device_class = device_class
        self._attr_options = options
        self._attr_entity_category = category

    @property
    def native_value(self) -> Any:
        """Attribute value; ENUM sensors drop values outside their options."""
        value = self._device.attributes.get(self._key)
        if self._attr_options is not None and value not in self._attr_options:
            return None
        return value


class WasherFinishTime(WasherEntity, SensorEntity):
    """When the running course ends; empty when no course is running."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, device: ToshibaWasher) -> None:
        """Initialize."""
        super().__init__(device, "finish_time")

    @property
    def native_value(self) -> datetime | None:
        """Now plus the remaining minutes."""
        minutes = self._device.attributes.get("time_remaining")
        if not minutes:
            return None
        return dt_util.utcnow().replace(second=0, microsecond=0) + timedelta(
            minutes=minutes
        )
