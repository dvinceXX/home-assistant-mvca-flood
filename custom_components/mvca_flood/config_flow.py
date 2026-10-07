"""Config flow for MVCA Flood & Low Water."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

SCAN_INTERVAL_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=5,
        max=1440,
        step=1,
        mode=NumberSelectorMode.BOX,
        unit_of_measurement="minutes",
    )
)


def _scan_interval_schema(default: int) -> vol.Schema:
    """Return the scan-interval form schema."""

    return vol.Schema(
        {
            vol.Required(CONF_SCAN_INTERVAL, default=default): SCAN_INTERVAL_SELECTOR,
        }
    )


def _normalized_options(user_input: dict[str, Any]) -> dict[str, int]:
    """Coerce selector values to stored option types."""

    return {CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}


class MVCAConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MVCA Flood & Low Water."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial setup."""

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="MVCA Flood & Low Water",
                data={},
                options=_normalized_options(user_input),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_scan_interval_schema(DEFAULT_SCAN_INTERVAL),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MVCAOptionsFlow:
        """Create the options flow."""

        return MVCAOptionsFlow()


class MVCAOptionsFlow(OptionsFlow):
    """Handle MVCA options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage the poll interval."""

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=_normalized_options(user_input),
            )

        current = int(
            self.config_entry.options.get(
                CONF_SCAN_INTERVAL,
                DEFAULT_SCAN_INTERVAL,
            )
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_scan_interval_schema(current),
        )
