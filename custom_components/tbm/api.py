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
        _LOGGER.debug("Recherche d'arrêts avec query: %s", query)

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    _LOGGER.error("Erreur API status: %s", response.status)
                    raise TBMApiError(f"Erreur API: {response.status}")
                
                data = await response.json()
                _LOGGER.debug("Données reçues de l'API")

                stops: list[TBMStop] = []
                
                siri = data.get("Siri")
                if not siri:
                    _LOGGER.warning("Pas de données Siri dans la réponse")
                    return stops
                
                delivery = siri.get("StopPointsDelivery")
                if not delivery:
                    _LOGGER.warning("Pas de StopPointsDelivery dans la réponse")
                    return stops
                
                stop_refs = delivery.get("AnnotatedStopPointRef", [])
                if not stop_refs:
                    _LOGGER.warning("Pas d'arrêts dans la réponse")
                    return stops

                query_lower = query.lower()
                for item in stop_refs:
                    try:
                        stop_id = self._get_value(item.get("StopPointRef"))
                        stop_name = self._get_value(item.get("StopName"))

                        if not stop_name or query_lower not in stop_name.lower():
                            continue

                        lines: list[str] = []
                        lines_data = item.get("Lines")
                        if lines_data and isinstance(lines_data, dict):
                            line_refs = lines_data.get("LineRef", [])
                            if line_refs:
                                for line in line_refs:
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
                    except Exception as err:
                        _LOGGER.warning("Erreur parsing arrêt: %s", err)
                        continue

                _LOGGER.debug("Trouvé %d arrêts correspondants", len(stops))
                return stops

        except aiohttp.ClientError as err:
            _LOGGER.error("Erreur de connexion: %s", err)
            raise TBMApiError(f"Erreur de connexion: {err}") from err
        except Exception as err:
            _LOGGER.exception("Erreur inattendue lors de la recherche: %s", err)
            raise TBMApiError(f"Erreur inattendue: {err}") from err

    async def get_realtime_departures(
        self, stop_id: str, line_id: str | None = None
    ) -> list[TBMDeparture]:
        """Récupérer les prochains départs en temps réel."""
        url = f"{TBM_STOP_MONITORING_URL}?AccountKey={TBM_API_KEY}&MonitoringRef={stop_id}"
        if line_id:
            url = f"{url}&LineRef={line_id}"

        _LOGGER.debug("Récupération des départs pour: %s", stop_id)

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    _LOGGER.error("Erreur API status: %s", response.status)
                    raise TBMApiError(f"Erreur API: {response.status}")

                data = await response.json()
                return self._parse_departures(data)

        except aiohttp.ClientError as err:
            _LOGGER.error("Erreur de connexion: %s", err)
            raise TBMApiError(f"Erreur de connexion: {err}") from err
        except Exception as err:
            _LOGGER.exception("Erreur inattendue: %s", err)
            raise TBMApiError(f"Erreur inattendue: {err}") from err

    def _parse_departures(self, data: dict[str, Any]) -> list[TBMDeparture]:
        """Parser les données de départ de l'API SIRI."""
        departures: list[TBMDeparture] = []

        siri = data.get("Siri")
        if not siri:
            return departures
        
        service_delivery = siri.get("ServiceDelivery")
        if not service_delivery:
            return departures
        
        deliveries = service_delivery.get("StopMonitoringDelivery", [])

        for delivery in deliveries:
            visits = delivery.get("MonitoredStopVisit", [])
            if not visits:
                continue

            for visit in visits:
                try:
                    journey = visit.get("MonitoredVehicleJourney", {})
                    if not journey:
                        continue
                    
                    call = journey.get("MonitoredCall", {})
                    if not call:
                        continue

                    line_ref = self._get_value(journey.get("LineRef"))
                    line_name = self._extract_line_name(line_ref)

                    # Extraction sécurisée des noms
                    destination = ""
                    dest_names = journey.get("DestinationName")
                    if dest_names and isinstance(dest_names, list) and len(dest_names) > 0:
                        destination = self._get_value(dest_names[0])

                    direction_name = ""
                    dir_names = journey.get("DirectionName")
                    if dir_names and isinstance(dir_names, list) and len(dir_names) > 0:
                        direction_name = self._get_value(dir_names[0])

                    stop_name = ""
                    stop_names = call.get("StopPointName")
                    if stop_names and isinstance(stop_names, list) and len(stop_names) > 0:
                        stop_name = self._get_value(stop_names[0])

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
                except Exception as err:
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
            return str(obj.get("value", ""))
        return str(obj)

    @staticmethod
    def _extract_line_name(line_ref: str) -> str:
        """Extraire le nom de la ligne depuis la référence."""
        # Format: bordeaux:Line:XX:LOC -> XX
        if not line_ref:
            return ""
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
        except (ValueError, AttributeError):
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
        except Exception:
            return False
