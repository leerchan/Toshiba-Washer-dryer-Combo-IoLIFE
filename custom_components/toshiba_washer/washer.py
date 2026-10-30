"""Toshiba 0x55 frames on top of stock midea-local's DB (washer) device.

Toshiba (manufacturer 0008) washers such as the TW-127XP2R ignore the Midea
AA query and only answer 55 AA CC 33 framed messages. Field layout from the
status block (messageBytes[0] == 0x00) shared by lua/db/T_0008_DB_24..30.lua,
checked against frames captured from a TW-127XP2R.
"""

import asyncio
from typing import Any, ClassVar, Unpack

from midealocal.const import DeviceType
from midealocal.device import SKIP_ATTRIBUTE, MideaDeviceInitKwargs, dict_translator
from midealocal.devices.db import DeviceAttributes, MideaDBDevice
from midealocal.message import (
    BoolParser,
    FunctionParser,
    IntParser,
    ListTypes,
    MessageBody,
    MessageRequest,
    MessageResponse,
    MessageType,
)

MACHINE_STATUS_POWER_OFF = 0x00
MACHINE_STATUS_RUNNING = 0x02
MACHINE_STATUS_PAUSE = 0x03
SECONDS_PER_MINUTE = 60
# The washer's Wi-Fi sleeps whenever it is off; retry often so a start shows up fast
RECONNECT_INTERVAL = 5  # seconds

# mode / program names from lua/db/T_0008_DB_30.lua (older versions are subsets)
MODES = {0x00: "none", 0x01: "wash_dry", 0x02: "wash", 0x03: "dry",
         0x04: "clean_care", 0x05: "care"}
PROGRAMS = {
    0x00: "none", 0x01: "standard", 0x02: "tub_clean", 0x03: "fast",
    0x04: "careful", 0x05: "sixty_wash", 0x06: "blanket", 0x07: "delicate",
    0x08: "tub_clean_dry", 0x09: "memory", 0x0A: "sterilization", 0x0B: "mute",
    0x0C: "soft", 0x0D: "delicate_dryer", 0x0E: "soak", 0x0F: "odor_eliminating",
    0x10: "empty", 0x11: "degerm", 0x12: "auto_care", 0x13: "auto_twice_wash",
    0x14: "prewash_plus", 0x15: "uv_wash_and_dry", 0x16: "uv_dry_with_rotation",
    0x17: "uv_dry_without_rotation", 0x18: "forty_five_wash",
    0x1C: "fragrant_and_delicate", 0x1D: "tick_extermination", 0x1E: "pollen",
    0x21: "app_course_1", 0x22: "app_course_2", 0x23: "app_course_3",
    0x24: "app_course", 0x25: "uv_wash", 0x26: "uv_without_rotation",
    0x27: "uv_with_rotation", 0x28: "uv_deodorize_without_rotation",
    0x29: "uv_deodorize_with_rotation", 0x30: "60_tub_clean",
    0x32: "tub_clean_wash_dry", 0x51: "sheets", 0x52: "lace_curtain",
    0x53: "towel", 0x54: "fleece", 0x55: "school_uniform_or_washable",
    0x56: "slacks_skirt", 0x57: "jeans", 0x58: "cap", 0x59: "down_jacket",
    0x5A: "bet_putt", 0x5B: "functional_underwear", 0x5C: "reusable_bag",
    0x5D: "duvet", 0x5E: "t_shirt_recovery", 0x5F: "sports_wear",
    0x81: "light_dirt", 0x82: "wash_thoroughly_and_rinse",
    0x83: "quick_wash_and_dry", 0x84: "yellowing_off",
    0x85: "disinfection_clothing", 0x86: "keep_water_temperature",
    0x87: "prewash", 0x91: "super_concentrated_soak",
    0x92: "no_rinse_and_delicate", 0x93: "t_shirt_recovery_pro", 0xA0: "customize",
}
# process_info bits, in course order (lua: process_info_wash .. _soft_keep)
STAGES = [(0x02, "wash"), (0x04, "rinse"), (0x08, "spin"), (0x10, "dry"),
          (0x20, "soft_keep")]
EXTRA_ATTRIBUTES = ("stage", "door_open", "drain_filter_clean",
                    "dry_filter_clean", "error_code")


class MessageQueryToshiba(MessageRequest):
    """Toshiba status query (the frame the IoLIFE app sends)."""

    def __init__(self, protocol_version: int) -> None:
        """Initialize."""
        super().__init__(
            device_type=DeviceType.DB,
            protocol_version=protocol_version,
            message_type=MessageType.query,
            body_type=ListTypes.X00,
            header_type=ListTypes.X55,
        )

    @property
    def _body(self) -> bytearray:
        return bytearray([])


def _time_remaining(data: bytearray) -> int | None:
    """Remaining minutes, rounded up, while a course is running or paused.

    Outside a course remain_time holds the selected course's planned duration.
    """
    if data[0] not in (MACHINE_STATUS_RUNNING, MACHINE_STATUS_PAUSE):
        return None
    seconds = int.from_bytes(data[1:5], "little")
    return -(-seconds // SECONDS_PER_MINUTE)


def _stage(data: bytearray) -> str | None:
    """Current stage while running or paused (process_info .. machine_status).

    process_info lists the course's stages still to do: a TW-127XP2R reported
    0x3e in standby and 0x30 (dry + soft_keep) with 57 min of drying left.
    ponytail: inferred from one running sample; check it during a real wash.
    """
    if data[4] not in (MACHINE_STATUS_RUNNING, MACHINE_STATUS_PAUSE):
        return None
    return next((name for bit, name in STAGES if data[0] & bit), None)


class ToshibaStatusBody(MessageBody):
    """Toshiba status block: machine_status (22), remain_time seconds (23-26)."""

    def __init__(self, body: bytearray) -> None:
        """Initialize."""
        super().__init__(
            body=body,
            parser_list=[
                FunctionParser(
                    "power",
                    22,
                    lambda data: data[0] != MACHINE_STATUS_POWER_OFF,
                    default_value=False,
                ),
                FunctionParser(
                    "start",
                    22,
                    lambda data: data[0] == MACHINE_STATUS_RUNNING,
                    default_value=False,
                ),
                IntParser("status", 22),
                FunctionParser(
                    "time_remaining",
                    22,
                    _time_remaining,
                    default_value=None,
                    length_in_bytes=5,
                ),
                IntParser("mode", 2),
                IntParser("program", 3),
                FunctionParser(
                    "stage", 18, _stage, default_value=None, length_in_bytes=5
                ),
                IntParser("error_code", 20, length_in_bytes=2),
                BoolParser("door_open", 27, bit=0, default_value=False),
                BoolParser("drain_filter_clean", 27, bit=2, default_value=False),
                BoolParser("dry_filter_clean", 28, bit=1, default_value=False),
            ],
        )


class ToshibaResponse(MessageResponse):
    """Toshiba 0x55 response; other frames carry no attributes."""

    def __init__(self, message: bytes) -> None:
        """Initialize."""
        super().__init__(bytearray(message))
        if (
            self.header_type == ListTypes.X55
            and self.message_type
            in [MessageType.set, MessageType.query, MessageType.notify1]
            and self.body_type == ListTypes.X00
        ):
            self.set_body(ToshibaStatusBody(super().body))
        self.set_attr()


class ToshibaWasher(MideaDBDevice):
    """Midea DB device that speaks Toshiba's 0x55 frames."""

    # machine_status: power_off, power_on, running, pause, finish; pop_up (0x50)
    # is transient and skipped
    _toshiba_status: ClassVar[dict[int, str]] = {
        0x00: "idle",
        0x01: "standby",
        0x02: "start",
        0x03: "pause",
        0x04: "end",
    }

    def __init__(self, **kwargs: Unpack[MideaDeviceInitKwargs]) -> None:
        """Initialize, adding the Toshiba-only attributes."""
        super().__init__(customize="", **kwargs)
        self._attributes.update(dict.fromkeys(EXTRA_ATTRIBUTES))
        self._attributes[DeviceAttributes.mode] = None
        self._attributes[DeviceAttributes.program] = None

    async def _connect_loop(self) -> None:
        """Reconnect every RECONNECT_INTERVAL seconds until the washer answers.

        Stock midea-local backs off up to 600 s and logs a warning per try,
        which hides a washer that was just switched on for up to 10 minutes.
        ponytail: overrides a private midea-local 14.0.0 method; recheck it if
        the pinned version changes.
        """
        while self._writer is None and self._is_run:
            if self._should_run() and not await self.connect(check_protocol=True):
                await self.close_socket()
                await asyncio.sleep(RECONNECT_INTERVAL)

    def build_query(self) -> list[MessageQueryToshiba]:  # type: ignore[override]
        """Query with the Toshiba frame."""
        return [MessageQueryToshiba(self._message_protocol_version)]

    def process_message(self, msg: bytes) -> dict[str, Any]:
        """Parse a Toshiba frame."""
        return self.update_attributes_from_message(
            ToshibaResponse(msg),
            {
                DeviceAttributes.status: dict_translator(
                    self._toshiba_status, SKIP_ATTRIBUTE
                ),
                DeviceAttributes.mode: lambda v: MODES.get(v, f"0x{v:02x}"),
                DeviceAttributes.program: lambda v: PROGRAMS.get(v, f"0x{v:02x}"),
            },
        )
