"""Client API pour TBM (Transports Bordeaux Métropole) - SIRI Lite."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp

from .const import (
    TBM_API_KEY,
    TBM_LINES_DISCOVERY_URL,
    TBM_STOP_MONITORING_URL,
    TBM_STOPPOINTS_DISCOVERY_URL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class TBMDeparture:
    """Représente un départ de tram/bus."""

    line: str
    line_name: str
    destination: str
    direction_name: str
    aimed_arrival: datetime | None
    expected_arrival: datetime | None
    waiting_time_minutes: int
    stop_name: str
    realtime: bool


@dataclass
class TBMStop:
    """Représente un arrêt TBM."""

    id: str
    name: str
    lines: list[str]


@dataclass
class TBMLine:
    """Représente une ligne TBM."""

    id: str
    name: str
    destinations: list[str]


class TBMApiError(Exception):
    """Exception pour les erreurs de l'API TBM."""


class TBMApiClient:
    """Client pour l'API SIRI Lite TBM."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialiser le client API."""
        self._session = session

    async def search_stops(self, query: str) -> list[TBMStop]:
        """Rechercher des arrêts par nom."""
        url = f"{TBM_STOPPOINTS_DISCOVERY_URL}?AccountKey={TBM_API_KEY}"

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise TBMApiError(f"Erreur API: {response.status}")
                data = await response.json()

                stops: list[TBMStop] = []
                stop_refs = (
                    data.get("Siri", {})
                    .get("StopPointsDelivery", {})
                    .get("AnnotatedStopPointRef", [])
                )

                query_lower = query.lower()
                for item in stop_refs:
                    stop_id = self._get_value(item.get("StopPointRef"))
                    stop_name = self._get_value(item.get("StopName"))

                    if query_lower in stop_name.lower():
                        lines = []
                        for line in item.get("Lines", {}).get("LineRef", []):
                            line_id = self._get_value(line)
                            if line_id:
                                lines.append(line_id)

                        stops.append(
                            TBMStop(
                                id=stop_id,
                                name=stop_name,
                                lines=lines,
                            )
                        )

                return stops

        except aiohttp.ClientError as err:
            raise TBMApiError(f"Erreur de connexion: {err}") from err

    async def get_all_stops(self) -> list[TBMStop]:
        """Obtenir tous les arrêts."""
        url = f"{TBM_STOPPOINTS_DISCOVERY_URL}?AccountKey={TBM_API_KEY}"

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise TBMApiError(f"Erreur API: {response.status}")
                data = await response.json()

                stops: list[TBMStop] = []
                stop_refs = (
                    data.get("Siri", {})
                    .get("StopPointsDelivery", {})
                    .get("AnnotatedStopPointRef", [])
                )

                for item in stop_refs:
                    stop_id = self._get_value(item.get("StopPointRef"))
                    stop_name = self._get_value(item.get("StopName"))

                    lines = []
                    for line in item.get("Lines", {}).get("LineRef", []):
                        line_id = self._get_value(line)
                        if line_id:
                            lines.append(line_id)

                    stops.append(
                        TBMStop(
                            id=stop_id,
                            name=stop_name,
                            lines=lines,
                        )
                    )

                return stops

        except aiohttp.ClientError as err:
            raise TBMApiError(f"Erreur de connexion: {err}") from err

    async def get_lines(self) -> list[TBMLine]:
        """Obtenir toutes les lignes."""
        url = f"{TBM_LINES_DISCOVERY_URL}?AccountKey={TBM_API_KEY}"

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise TBMApiError(f"Erreur API: {response.status}")
                data = await response.json()

                lines: list[TBMLine] = []
                line_refs = (
                    data.get("Siri", {})
                    .get("LinesDelivery", {})
                    .get("AnnotatedLineRef", [])
                )

                for item in line_refs:
                    line_id = self._get_value(item.get("LineRef"))
                    line_name = self._get_value(item.get("LineName"))

                    destinations = []
                    for dest in item.get("Destinations", {}).get("Destination", []):
                        dest_name = self._get_value(dest.get("DestinationName"))
                        if dest_name:
                            destinations.append(dest_name)

                    lines.append(
                        TBMLine(
                            id=line_id,
                            name=line_name,
                            destinations=destinations,
                        )
                    )

                return lines

        except aiohttp.ClientError as err:
            raise TBMApiError(f"Erreur de connexion: {err}") from err

    async def get_realtime_departures(
        self, stop_id: str, line_id: str | None = None
    ) -> list[TBMDeparture]:
        """Récupérer les prochains départs en temps réel."""
        url = f"{TBM_STOP_MONITORING_URL}?AccountKey={TBM_API_KEY}&MonitoringRef={stop_id}"
        if line_id:
            url = f"{url}&LineRef={line_id}"

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise TBMApiError(f"Erreur API: {response.status}")

                data = await response.json()
                return self._parse_departures(data)

        except aiohttp.ClientError as err:
            raise TBMApiError(f"Erreur de connexion: {err}") from err

    def _parse_departures(self, data: dict[str, Any]) -> list[TBMDeparture]:
        """Parser les données de départ de l'API SIRI."""
        departures: list[TBMDeparture] = []

        deliveries = (
            data.get("Siri", {})
            .get("ServiceDelivery", {})
            .get("StopMonitoringDelivery", [])
        )

        for delivery in deliveries:
            visits = delivery.get("MonitoredStopVisit", [])

            for visit in visits:
                try:
                    journey = visit.get("MonitoredVehicleJourney", {})
                    call = journey.get("MonitoredCall", {})

                    line_ref = self._get_value(journey.get("LineRef"))
                    line_name = self._extract_line_name(line_ref)

                    destination = self._get_value(
                        journey.get("DestinationName", [{}])[0]
                        if journey.get("DestinationName")
                        else {}
                    )
                    direction_name = self._get_value(
                        journey.get("DirectionName", [{}])[0]
                        if journey.get("DirectionName")
                        else {}
                    )
                    stop_name = self._get_value(
                        call.get("StopPointName", [{}])[0]
                        if call.get("StopPointName")
                        else {}
                    )

                    aimed_arrival = self._parse_datetime(call.get("AimedArrivalTime"))
                    expected_arrival = self._parse_datetime(call.get("ExpectedArrivalTime"))

                    # Calculer le temps d'attente
                    waiting_time = self._calculate_waiting_time(expected_arrival or aimed_arrival)

                    departures.append(
                        TBMDeparture(
                            line=line_ref,
                            line_name=line_name,
                            destination=destination,
                            direction_name=direction_name,
                            aimed_arrival=aimed_arrival,
                            expected_arrival=expected_arrival,
                            waiting_time_minutes=waiting_time,
                            stop_name=stop_name,
                            realtime=expected_arrival is not None,
                        )
                    )
                except (KeyError, IndexError, ValueError) as err:
                    _LOGGER.warning("Erreur parsing départ: %s", err)
                    continue

        # Trier par temps d'attente
        departures.sort(key=lambda x: x.waiting_time_minutes)
        return departures

    @staticmethod
    def _get_value(obj: Any) -> str:
        """Extraire la valeur d'un objet SIRI (peut être dict ou str)."""
        if obj is None:
            return ""
        if isinstance(obj, dict):
            return obj.get("value", "")
        return str(obj)

    @staticmethod
    def _extract_line_name(line_ref: str) -> str:
        """Extraire le nom de la ligne depuis la référence."""
        # Format: bordeaux:Line:XX:LOC -> XX
        if ":" in line_ref:
            parts = line_ref.split(":")
            if len(parts) >= 3:
                return parts[2]
        return line_ref

    @staticmethod
    def _parse_datetime(dt_str: str | None) -> datetime | None:
        """Parser une date ISO 8601."""
        if not dt_str:
            return None
        try:
            # Format: 2025-11-25T14:03:57Z
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _calculate_waiting_time(arrival: datetime | None) -> int:
        """Calculer le temps d'attente en minutes."""
        if not arrival:
            return 999

        now = datetime.now(timezone.utc)
        delta = arrival - now
        minutes = int(delta.total_seconds() / 60)
        return max(0, minutes)

    async def test_connection(self) -> bool:
        """Tester la connexion à l'API."""
        try:
            url = f"{TBM_STOPPOINTS_DISCOVERY_URL}?AccountKey={TBM_API_KEY}"
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return response.status == 200
        except aiohttp.ClientError:
            return False
