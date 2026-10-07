"""Config flow for MVCA Flood & Low Water."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


class MVCAConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for MVCA Flood & Low Water."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ):
        """Handle the initial setup."""

        if self._async_current_entries():
            return self.async_abort(
                reason="single_instance_allowed"
            )

        if user_input is not None:
            return self.async_create_entry(
                title="MVCA Flood & Low Water",
                data={},
                options=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=5, max=1440),
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )