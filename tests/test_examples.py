"""Run the examples/live_activity.*.yaml blueprints against fake washer states."""

from datetime import timedelta
from pathlib import Path
import shutil

import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

EXAMPLES = Path(__file__).parent.parent / "examples"
# Entity IDs deliberately share no common prefix: the blueprint must not assume one.
INPUTS = {
    "notify_target": "notify.test_phone",
    "status_entity": "sensor.a_status",
    "stage_entity": "sensor.b_stage",
    "finish_time_entity": "sensor.c_finish",
    "mode_entity": "sensor.d_mode",
    "program_entity": "sensor.e_program",
    "error_code_entity": "sensor.f_error",
    "door_entity": "binary_sensor.g_door",
    "drain_filter_entity": "binary_sensor.h_drain",
    "dryer_filter_entity": "binary_sensor.i_dryer",
}


@pytest.mark.parametrize("lang", ["en", "zh-Hans", "ja"])
async def test_live_activity_blueprint(
    hass: HomeAssistant, tmp_path: Path, lang: str
) -> None:
    """Stage changes update the Live Activity; end, errors and filters notify."""
    hass.config.config_dir = str(tmp_path)
    folder = tmp_path / "blueprints/automation/toshiba_washer"
    folder.mkdir(parents=True)
    shutil.copy(EXAMPLES / f"live_activity.{lang}.yaml", folder)
    calls = async_mock_service(hass, "notify", "test_phone")

    finish = (dt_util.utcnow() + timedelta(minutes=60)).isoformat()
    for entity_id, state in [
        (INPUTS["status_entity"], "standby"), (INPUTS["stage_entity"], "unknown"),
        (INPUTS["finish_time_entity"], finish),
        (INPUTS["mode_entity"], "wash_dry"), (INPUTS["program_entity"], "standard"),
        (INPUTS["error_code_entity"], "0"), (INPUTS["door_entity"], "off"),
        (INPUTS["drain_filter_entity"], "off"), (INPUTS["dryer_filter_entity"], "off"),
    ]:
        hass.states.async_set(entity_id, state)
    assert await async_setup_component(hass, "automation", {"automation": {
        "use_blueprint": {
            "path": f"toshiba_washer/live_activity.{lang}.yaml", "input": INPUTS,
        }
    }})

    hass.states.async_set(INPUTS["status_entity"], "start")
    hass.states.async_set(INPUTS["stage_entity"], "rinse")
    await hass.async_block_till_done()
    data = calls[-1].data["data"]
    assert data["tag"] == "toshiba_washer" and data["live_update"] is True
    assert 25 <= data["progress"] < 45 and data["chronometer"] is True
    assert "silent" not in data

    hass.states.async_set(INPUTS["stage_entity"], "soft_keep")
    await hass.async_block_till_done()
    assert calls[-1].data["data"]["progress"] == 100

    hass.states.async_set(INPUTS["status_entity"], "end")
    await hass.async_block_till_done()
    assert calls[-1].data["data"]["notification_icon"] == "mdi:check-circle"

    hass.states.async_set(INPUTS["door_entity"], "on")
    await hass.async_block_till_done()
    assert calls[-1].data["message"] == "clear_notification"

    hass.states.async_set(INPUTS["error_code_entity"], "21")
    await hass.async_block_till_done()
    assert "21" in calls[-1].data["message"]

    hass.states.async_set(INPUTS["drain_filter_entity"], "on")
    await hass.async_block_till_done()
    drain = calls[-1].data
    hass.states.async_set(INPUTS["dryer_filter_entity"], "on")
    await hass.async_block_till_done()
    dryer = calls[-1].data
    assert drain["message"] != dryer["message"]
    assert dryer["data"]["tag"] == "toshiba_washer_i_dryer"
    assert len(calls) == 7
    # drop the 5-minute time_pattern timer before teardown
    await hass.services.async_call(
        "automation", "turn_off", {"entity_id": "all"}, blocking=True
    )
