"""Config flow: one IoLIFE login to fetch the washer's LAN token/key."""

import logging
from typing import Any

import aiohttp
from midealocal.cloud import get_midea_cloud
from midealocal.const import ProtocolVersion
from midealocal.exceptions import MideaLocalError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import DOMAIN, WASHER_TYPE, create_device

_LOGGER = logging.getLogger(__name__)
CLOUD_NAME = "Toshiba Iolife"

SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): str,
        vol.Required("ip_address"): str,
    }
)


class WasherError(Exception):
    """Setup failure; the message is a translation key."""


class ToshibaWasherConfigFlow(ConfigFlow, domain=DOMAIN):
    """Toshiba washer config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the IoLIFE login and the washer's IP address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                data = await self._fetch_washer(user_input)
            except WasherError as err:
                errors["base"] = str(err)
            except (MideaLocalError, aiohttp.ClientError, OSError):
                _LOGGER.exception("Toshiba washer setup failed")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(str(data["device_id"]))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data["name"], data=data)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input),
            errors=errors,
        )

    async def _fetch_washer(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Find the washer in the account and the token/key it accepts."""
        cloud = get_midea_cloud(
            CLOUD_NAME,
            async_get_clientsession(self.hass),
            user_input["email"],
            user_input["password"],
        )
        if not await cloud.login():
            raise WasherError("login_failed")
        appliances = await cloud.list_appliances()
        device_id, info = next(
            ((i, a) for i, a in appliances.items() if a["type"] == WASHER_TYPE),
            (None, None),
        )
        if device_id is None or info is None:
            raise WasherError("no_washer")
        base = {
            "name": info["name"] or "Washer",
            "device_id": device_id,
            "ip_address": user_input["ip_address"],
            "protocol": int(ProtocolVersion.V3),
            "model": info["model"],
            "sn": info["sn"],
        }
        for key in (await cloud.get_cloud_keys(device_id)).values():
            data = {**base, "token": key["token"], "key": key["key"]}
            device = create_device(data)
            try:
                if await device.connect(check_protocol=True):
                    return data
            finally:
                await device.close_socket()
        raise WasherError("cannot_connect")
