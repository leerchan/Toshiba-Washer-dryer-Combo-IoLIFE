"""Tests for custom_components/toshiba_washer (run with pytest-homeassistant-custom-component)."""

from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.toshiba_washer import DOMAIN
from custom_components.toshiba_washer.washer import MessageQueryToshiba, ToshibaWasher
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

# Frames captured from a TW-127XP2R. Running: machine_status 0x02, 3419 s left.
RUNNING = bytes.fromhex(
    "55aacc333d0001db000000000000038000ff01012a00002d170e03f1040000024001301200"
    "00025b0d00000000000e03030e03000106232363630a0a3e34bcfe9c"
)
# Standby (machine_status 0x01): remain_time is the course's planned 401 min.
STANDBY = bytes.fromhex(
    "55aacc333d0001db000000000000038000ff010126070039000e03f10400000240013e0000"
    "0001fc5d00000000000e03030e03000106232363630a0a00400551e9"
)
ENTRY_DATA = {
    "name": "Washer",
    "device_id": 123456789012345,
    "ip_address": "192.168.1.50",
    "protocol": 3,
    "model": "TW-127XP2R",
    "sn": "0008DB12000000000000000000000000",
    "token": "AA",
    "key": "BB",
}


def _washer() -> ToshibaWasher:
    return ToshibaWasher(
        name="Washer", device_id=1, ip_address="192.168.1.50", port=6444,
        token="AA", key="BB", device_protocol=3, model="TW-127XP2R",
        subtype=0, serial_number=ENTRY_DATA["sn"],
    )


def test_query_matches_iolife_app() -> None:
    """Same bytes the IoLIFE app sends."""
    assert MessageQueryToshiba(1).serialize() == bytes.fromhex(
        "55aacc330f0001db000000000000030000e687"
    )
    assert isinstance(_washer().build_query()[0], MessageQueryToshiba)


def test_parse_running_and_standby() -> None:
    """Running reports a countdown, standby does not."""
    washer = _washer()
    status = washer.process_message(RUNNING)
    assert status["status"] == "start"
    assert status["power"] is True
    assert status["time_remaining"] == 57
    assert status["stage"] == "dry"  # process_info 0x30: dry + soft_keep left
    status = washer.process_message(STANDBY)
    assert status["status"] == "standby"
    assert status["start"] is False
    assert status["time_remaining"] is None
    assert status["stage"] is None
    assert status["mode"] == "wash_dry"
    assert status["program"] == "standard"
    assert status["door_open"] is False
    assert status["drain_filter_clean"] is False
    assert status["dry_filter_clean"] is False
    assert status["error_code"] == 0


def _cloud(connect_ok: bool = True) -> tuple[MagicMock, bool]:
    cloud = MagicMock()
    cloud.login = AsyncMock(return_value=True)
    cloud.list_appliances = AsyncMock(
        return_value={
            999: {"type": 0xAC, "name": "AC", "sn": "", "model": ""},
            ENTRY_DATA["device_id"]: {
                "type": 0xDB, "name": "Washer", "sn": ENTRY_DATA["sn"],
                "model": "TW-127XP2R",
            },
        }
    )
    cloud.get_cloud_keys = AsyncMock(return_value={1: {"token": "AA", "key": "BB"}})
    return cloud, connect_ok


async def _run_flow(hass: HomeAssistant, connect_ok: bool):
    cloud, _ = _cloud()
    with (
        patch("custom_components.toshiba_washer.config_flow.get_midea_cloud", return_value=cloud),
        patch.object(ToshibaWasher, "connect", AsyncMock(return_value=connect_ok)),
        patch.object(ToshibaWasher, "close_socket", AsyncMock()) as close_socket,
        patch("custom_components.toshiba_washer.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"email": "a@b.c", "password": "pw", "ip_address": "192.168.1.50"},
        )
        close_socket.assert_awaited()
    return result


async def test_config_flow_creates_entry(hass: HomeAssistant) -> None:
    """Login, pick the washer, keep the working key."""
    result = await _run_flow(hass, connect_ok=True)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == ENTRY_DATA


async def test_config_flow_washer_unreachable(hass: HomeAssistant) -> None:
    """Asleep washer: ask again instead of saving."""
    result = await _run_flow(hass, connect_ok=False)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_sensors_follow_device(hass: HomeAssistant) -> None:
    """Entities are unavailable while asleep and update on pushed status."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, unique_id="1")
    entry.add_to_hass(hass)
    with (
        patch.object(ToshibaWasher, "open", AsyncMock()),
        patch.object(ToshibaWasher, "close", AsyncMock()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get("sensor.washer_status").state == "unavailable"

        washer = entry.runtime_data
        washer.process_message(RUNNING)
        washer.set_available(True)
        await hass.async_block_till_done()
        assert hass.states.get("sensor.washer_status").state == "start"
        assert hass.states.get("sensor.washer_finish_time").state not in (
            "unknown", "unavailable",
        )

        assert hass.states.get("sensor.washer_stage").state == "dry"

        washer.update_all(washer.process_message(STANDBY))
        await hass.async_block_till_done()
        assert hass.states.get("sensor.washer_status").state == "standby"
        assert hass.states.get("sensor.washer_finish_time").state == "unknown"
        assert hass.states.get("sensor.washer_stage").state == "unknown"
        assert hass.states.get("sensor.washer_mode").state == "wash_dry"
        assert hass.states.get("sensor.washer_program").state == "standard"
        assert hass.states.get("sensor.washer_error_code").state == "0"
        assert hass.states.get("binary_sensor.washer_door").state == "off"
        assert hass.states.get("binary_sensor.washer_drain_filter_needs_cleaning").state == "off"
        assert hass.states.get("binary_sensor.washer_dryer_filter_needs_cleaning").state == "off"

        assert await hass.config_entries.async_unload(entry.entry_id)


def test_translations_cover_every_state() -> None:
    """zh-Hans and ja have a name for every entity and every state en has."""
    import json
    from pathlib import Path

    base = Path(__file__).parent.parent / "custom_components/toshiba_washer/translations"

    def keys(d, prefix=""):
        out = set()
        for k, v in d.items():
            out |= keys(v, f"{prefix}{k}.") if isinstance(v, dict) else {prefix + k}
        return out

    en = keys(json.loads((base / "en.json").read_text()))
    for lang in ("zh-Hans", "ja"):
        assert keys(json.loads((base / f"{lang}.json").read_text())) == en, lang


async def test_reconnects_every_few_seconds() -> None:
    """A sleeping washer is retried at a fixed short interval, not backed off."""
    from custom_components.toshiba_washer.washer import RECONNECT_INTERVAL

    washer = _washer()
    washer._is_run = True
    attempts = 0

    async def connect(check_protocol: bool = False) -> bool:
        nonlocal attempts
        attempts += 1
        if attempts < 4:  # off for three tries, then switched on
            return False
        washer._writer = MagicMock()
        return True

    with (
        patch.object(washer, "connect", connect),
        patch.object(washer, "close_socket", AsyncMock()),
        patch("custom_components.toshiba_washer.washer.asyncio.sleep", AsyncMock()) as sleep,
    ):
        await washer._connect_loop()
    assert attempts == 4
    assert [c.args[0] for c in sleep.await_args_list] == [RECONNECT_INTERVAL] * 3
