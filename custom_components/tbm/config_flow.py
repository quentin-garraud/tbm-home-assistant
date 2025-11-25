"""Config flow pour l'intégration TBM."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import TBMApiClient, TBMApiError, TBMStop
from .const import CONF_LINE_ID, CONF_STOP_ID, CONF_STOP_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class TBMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestionnaire du flux de configuration pour TBM."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialiser le flux de configuration."""
        self._stops: list[TBMStop] = []
        self._selected_stop: TBMStop | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Gérer l'étape utilisateur initiale - recherche d'arrêt."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = user_input.get("query", "").strip()
            _LOGGER.debug("Recherche d'arrêt: %s", query)

            if len(query) < 2:
                errors["base"] = "query_too_short"
            else:
                session = async_get_clientsession(self.hass)
                api = TBMApiClient(session)

                try:
                    # Rechercher les arrêts correspondants
                    self._stops = await api.search_stops(query)
                    _LOGGER.debug("Arrêts trouvés: %d", len(self._stops))

                    if not self._stops:
                        errors["base"] = "stop_not_found"
                    else:
                        # Passer à l'étape de sélection d'arrêt
                        return await self.async_step_select_stop()

                except TBMApiError as err:
                    _LOGGER.error("Erreur API TBM: %s", err)
                    errors["base"] = "cannot_connect"
                except Exception as err:
                    _LOGGER.exception("Erreur inattendue dans config_flow: %s", err)
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("query"): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "example": "Berges du Lac, Quinconces, Victoire..."
            },
        )

    async def async_step_select_stop(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Gérer la sélection de l'arrêt parmi les résultats."""
        errors: dict[str, str] = {}

        if user_input is not None:
            stop_id = user_input.get(CONF_STOP_ID)
            _LOGGER.debug("Arrêt sélectionné: %s", stop_id)

            # Trouver l'arrêt sélectionné
            for stop in self._stops:
                if stop.id == stop_id:
                    self._selected_stop = stop
                    break

            if self._selected_stop:
                # Vérifier que cet arrêt n'est pas déjà configuré
                await self.async_set_unique_id(stop_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"TBM - {self._selected_stop.name}",
                    data={
                        CONF_STOP_ID: self._selected_stop.id,
                        CONF_STOP_NAME: self._selected_stop.name,
                    },
                )
            else:
                errors["base"] = "unknown"

        # Construire la liste des arrêts pour la sélection
        stop_options: list[dict[str, str]] = []

        for stop in self._stops:
            # Extraire le numéro de l'arrêt depuis l'ID (ex: bordeaux:StopPoint:BP:7132:LOC -> 7132)
            stop_num = ""
            if stop.id and ":" in stop.id:
                parts = stop.id.split(":")
                if len(parts) >= 4:
                    stop_num = parts[3]
            
            # Afficher le nom avec le numéro d'arrêt pour identifier facilement
            display_name = f"{stop.name} (ID: {stop_num})"
            stop_options.append({"value": stop.id, "label": display_name})

        _LOGGER.debug("Options d'arrêts: %d", len(stop_options))

        return self.async_show_form(
            step_id="select_stop",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STOP_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=stop_options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"count": str(len(self._stops))},
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
