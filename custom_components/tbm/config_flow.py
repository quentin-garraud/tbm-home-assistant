"""Config flow pour l'intégration TBM."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TBMApiClient, TBMApiError
from .const import CONF_LINE_ID, CONF_STOP_ID, CONF_STOP_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class TBMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestionnaire du flux de configuration pour TBM."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialiser le flux de configuration."""
        self._stop_id: str | None = None
        self._stop_name: str | None = None
        self._available_lines: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Gérer l'étape utilisateur initiale."""
        errors: dict[str, str] = {}

        if user_input is not None:
            stop_id = user_input[CONF_STOP_ID].strip()

            session = async_get_clientsession(self.hass)
            api = TBMApiClient(session)

            try:
                # Vérifier si c'est un ID d'arrêt valide
                stop_info = await api.get_stop_info(stop_id)
                if stop_info and stop_info.name:
                    self._stop_id = stop_id
                    self._stop_name = stop_info.name
                    self._available_lines = stop_info.lines

                    # Passer à l'étape de sélection de ligne
                    return await self.async_step_line()

                # Sinon, essayer de chercher par nom
                stops = await api.search_stops(stop_id)
                if stops:
                    # Pour simplifier, prendre le premier résultat
                    self._stop_id = stops[0].id
                    self._stop_name = stops[0].name
                    self._available_lines = stops[0].lines
                    return await self.async_step_line()

                errors["base"] = "stop_not_found"

            except TBMApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Erreur inattendue")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STOP_ID): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "example_stop": "stop_area:TBM:SA:QUIN (Quinconces)"
            },
        )

    async def async_step_line(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Gérer l'étape de sélection de ligne (optionnel)."""
        if user_input is not None:
            line_id = user_input.get(CONF_LINE_ID)

            # Vérifier que cet arrêt n'est pas déjà configuré
            await self.async_set_unique_id(f"{self._stop_id}_{line_id or 'all'}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"TBM - {self._stop_name}",
                data={
                    CONF_STOP_ID: self._stop_id,
                    CONF_STOP_NAME: self._stop_name,
                    CONF_LINE_ID: line_id if line_id != "all" else None,
                },
            )

        # Construire la liste des lignes disponibles
        line_options = {"all": "Toutes les lignes"}
        for line in self._available_lines:
            line_id = line.get("id", "")
            line_name = line.get("name", line_id)
            if line_id:
                line_options[line_id] = line_name

        return self.async_show_form(
            step_id="line",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LINE_ID, default="all"): vol.In(line_options),
                }
            ),
            description_placeholders={"stop_name": self._stop_name},
        )


class TBMOptionsFlow(config_entries.OptionsFlow):
    """Gestionnaire des options pour TBM."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialiser le flux d'options."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Gérer les options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )

