"""Client API pour TBM (Transports Bordeaux Métropole)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp

from .const import TBM_API_BASE_URL

_LOGGER = logging.getLogger(__name__)


@dataclass
class TBMDeparture:
    """Représente un départ de tram/bus."""

    line: str
    line_color: str
    destination: str
    departure_time: str
    waiting_time_minutes: int
    vehicle_type: str
    realtime: bool


@dataclass
class TBMStop:
    """Représente un arrêt TBM."""

    id: str
    name: str
    city: str
    lines: list[dict[str, Any]]


class TBMApiError(Exception):
    """Exception pour les erreurs de l'API TBM."""


class TBMApiClient:
    """Client pour l'API TBM."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialiser le client API."""
        self._session = session
        self._base_url = TBM_API_BASE_URL

    async def search_stops(self, query: str) -> list[TBMStop]:
        """Rechercher des arrêts par nom."""
        url = f"{self._base_url}/network/stoparea-informations/{query}"

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    raise TBMApiError(f"Erreur API: {response.status}")
                data = await response.json()

                stops = []
                if isinstance(data, list):
                    for item in data:
                        stops.append(
                            TBMStop(
                                id=item.get("id", ""),
                                name=item.get("name", ""),
                                city=item.get("city", ""),
                                lines=item.get("lines", []),
                            )
                        )
                return stops
        except aiohttp.ClientError as err:
            raise TBMApiError(f"Erreur de connexion: {err}") from err

    async def get_stop_info(self, stop_id: str) -> TBMStop | None:
        """Obtenir les informations d'un arrêt."""
        url = f"{self._base_url}/network/stoparea-informations/{stop_id}"

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None
                data = await response.json()

                if isinstance(data, dict):
                    return TBMStop(
                        id=data.get("id", stop_id),
                        name=data.get("name", ""),
                        city=data.get("city", ""),
                        lines=data.get("lines", []),
                    )
                return None
        except aiohttp.ClientError as err:
            _LOGGER.error("Erreur lors de la récupération de l'arrêt: %s", err)
            return None

    async def get_realtime_departures(
        self, stop_id: str, line_id: str | None = None
    ) -> list[TBMDeparture]:
        """Récupérer les prochains départs en temps réel."""
        url = f"{self._base_url}/get-realtime-pass/{stop_id}"
        if line_id:
            url = f"{url}/{line_id}"

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    raise TBMApiError(f"Erreur API: {response.status}")

                data = await response.json()
                return self._parse_departures(data)

        except aiohttp.ClientError as err:
            raise TBMApiError(f"Erreur de connexion: {err}") from err

    def _parse_departures(self, data: dict[str, Any]) -> list[TBMDeparture]:
        """Parser les données de départ de l'API."""
        departures: list[TBMDeparture] = []

        if not isinstance(data, dict) or "destinations" not in data:
            return departures

        for destination_data in data.get("destinations", {}).values():
            for schedule in destination_data:
                try:
                    waiting_time = self._parse_waiting_time(
                        schedule.get("waittime", "")
                    )
                    departures.append(
                        TBMDeparture(
                            line=schedule.get("ligne", ""),
                            line_color=schedule.get("lineColor", "#000000"),
                            destination=schedule.get("destination", ""),
                            departure_time=schedule.get("arrival", ""),
                            waiting_time_minutes=waiting_time,
                            vehicle_type=schedule.get("vehicleType", "tram"),
                            realtime=schedule.get("realtime", False),
                        )
                    )
                except (KeyError, ValueError) as err:
                    _LOGGER.warning("Erreur parsing départ: %s", err)
                    continue

        # Trier par temps d'attente
        departures.sort(key=lambda x: x.waiting_time_minutes)
        return departures

    @staticmethod
    def _parse_waiting_time(waittime: str) -> int:
        """Convertir le temps d'attente en minutes."""
        if not waittime:
            return 999

        # Format: "HH:MM:SS" ou "MM:SS" ou "Proche"
        if waittime.lower() in ("proche", "immin.", "imminent"):
            return 0

        try:
            parts = waittime.split(":")
            if len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 2:  # MM:SS
                return int(parts[0])
            else:
                return int(waittime)
        except ValueError:
            return 999

    async def test_connection(self) -> bool:
        """Tester la connexion à l'API."""
        try:
            # Test avec un arrêt connu (Quinconces)
            url = f"{self._base_url}/network/stoparea-informations/stop_area:TBM:SA:QUIN"
            async with self._session.get(url) as response:
                return response.status == 200
        except aiohttp.ClientError:
            return False

