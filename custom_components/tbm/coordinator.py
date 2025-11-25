"""Coordinateur de données pour l'intégration TBM."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TBMApiClient, TBMApiError, TBMDeparture
from .const import CONF_LINE_ID, CONF_STOP_ID, CONF_STOP_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class TBMDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinateur pour les mises à jour des données TBM."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialiser le coordinateur."""
        self.stop_id = entry.data[CONF_STOP_ID]
        self.stop_name = entry.data.get(CONF_STOP_NAME, self.stop_id)
        self.line_id = entry.data.get(CONF_LINE_ID)

        session = async_get_clientsession(hass)
        self.api = TBMApiClient(session)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.stop_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupérer les données depuis l'API TBM."""
        try:
            departures = await self.api.get_realtime_departures(
                self.stop_id, self.line_id
            )

            # Grouper par ligne et direction
            grouped: dict[str, list[TBMDeparture]] = {}
            for dep in departures:
                key = f"{dep.line_name}_{dep.destination}"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(dep)

            return {
                "stop_id": self.stop_id,
                "stop_name": self.stop_name,
                "departures": departures,
                "grouped_departures": grouped,
                "next_departure": departures[0] if departures else None,
            }

        except TBMApiError as err:
            raise UpdateFailed(f"Erreur lors de la mise à jour: {err}") from err
