"""Capteurs pour l'intégration TBM."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AIMED_TIME,
    ATTR_DEPARTURE_TIME,
    ATTR_DESTINATION,
    ATTR_EXPECTED_TIME,
    ATTR_LINE,
    ATTR_NEXT_DEPARTURES,
    ATTR_REALTIME,
    ATTR_STOP_NAME,
    ATTR_WAITING_TIME,
    CONF_LINE_ID,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    DOMAIN,
)
from .coordinator import TBMDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurer les capteurs TBM depuis une entrée de configuration."""
    coordinator: TBMDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        TBMNextDepartureSensor(coordinator, entry),
    ]

    # Créer un capteur par ligne/direction si des données existent
    if coordinator.data and coordinator.data.get("grouped_departures"):
        for key in coordinator.data["grouped_departures"]:
            entities.append(TBMLineSensor(coordinator, entry, key))

    async_add_entities(entities)


class TBMBaseSensor(CoordinatorEntity[TBMDataUpdateCoordinator], SensorEntity):
    """Classe de base pour les capteurs TBM."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TBMDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialiser le capteur."""
        super().__init__(coordinator)
        self._entry = entry
        self._stop_id = entry.data[CONF_STOP_ID]
        self._stop_name = entry.data.get(CONF_STOP_NAME, self._stop_id)
        self._line_id = entry.data.get(CONF_LINE_ID)

    @property
    def device_info(self) -> dict[str, Any]:
        """Retourner les informations sur l'appareil."""
        return {
            "identifiers": {(DOMAIN, self._stop_id)},
            "name": f"TBM - {self._stop_name}",
            "manufacturer": "TBM - Transports Bordeaux Métropole",
            "model": "Arrêt de transport",
        }


class TBMNextDepartureSensor(TBMBaseSensor):
    """Capteur pour le prochain départ."""

    _attr_icon = "mdi:tram"

    def __init__(
        self,
        coordinator: TBMDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialiser le capteur de prochain départ."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._stop_id}_next"
        self._attr_name = "Prochain départ"

    @property
    def native_value(self) -> str | None:
        """Retourner le temps d'attente du prochain départ."""
        if not self.coordinator.data:
            return None

        next_dep = self.coordinator.data.get("next_departure")
        if not next_dep:
            return "Aucun"

        if next_dep.waiting_time_minutes <= 0:
            return "Imminent"
        elif next_dep.waiting_time_minutes == 1:
            return "1 min"
        else:
            return f"{next_dep.waiting_time_minutes} min"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Retourner les attributs supplémentaires."""
        if not self.coordinator.data:
            return {}

        attrs: dict[str, Any] = {
            ATTR_STOP_NAME: self._stop_name,
        }

        next_dep = self.coordinator.data.get("next_departure")
        if next_dep:
            attrs.update(
                {
                    ATTR_LINE: next_dep.line_name,
                    ATTR_DESTINATION: next_dep.destination,
                    ATTR_WAITING_TIME: next_dep.waiting_time_minutes,
                    ATTR_REALTIME: next_dep.realtime,
                }
            )
            if next_dep.aimed_arrival:
                attrs[ATTR_AIMED_TIME] = next_dep.aimed_arrival.isoformat()
            if next_dep.expected_arrival:
                attrs[ATTR_EXPECTED_TIME] = next_dep.expected_arrival.isoformat()

        # Liste des prochains départs
        departures = self.coordinator.data.get("departures", [])
        next_departures = []
        for dep in departures[:5]:  # Limiter à 5
            dep_info = {
                "line": dep.line_name,
                "destination": dep.destination,
                "waiting_time": dep.waiting_time_minutes,
                "realtime": dep.realtime,
            }
            if dep.expected_arrival:
                dep_info["expected_time"] = dep.expected_arrival.isoformat()
            next_departures.append(dep_info)
        attrs[ATTR_NEXT_DEPARTURES] = next_departures

        return attrs

    @property
    def icon(self) -> str:
        """Retourner l'icône basée sur le type de ligne."""
        if not self.coordinator.data:
            return "mdi:tram"

        next_dep = self.coordinator.data.get("next_departure")
        if not next_dep:
            return "mdi:tram"

        # Lignes de tram: A, B, C, D (ou 01, 02, 03, 04)
        line = next_dep.line_name.upper()
        if line in ("A", "B", "C", "D", "01", "02", "03", "04"):
            return "mdi:tram"
        # BatCub (navettes fluviales)
        if "BAT" in line:
            return "mdi:ferry"
        # Sinon c'est un bus
        return "mdi:bus"


class TBMLineSensor(TBMBaseSensor):
    """Capteur pour une ligne spécifique."""

    def __init__(
        self,
        coordinator: TBMDataUpdateCoordinator,
        entry: ConfigEntry,
        line_key: str,
    ) -> None:
        """Initialiser le capteur de ligne."""
        super().__init__(coordinator, entry)
        self._line_key = line_key
        parts = line_key.split("_", 1)
        self._line = parts[0] if parts else line_key
        self._direction = parts[1] if len(parts) > 1 else ""

        # Nettoyer l'ID unique
        safe_key = line_key.replace(":", "_").replace(" ", "_")
        self._attr_unique_id = f"{self._stop_id}_{safe_key}"
        self._attr_name = f"Ligne {self._line} → {self._direction}"

    @property
    def native_value(self) -> str | None:
        """Retourner le temps d'attente pour cette ligne."""
        if not self.coordinator.data:
            return None

        grouped = self.coordinator.data.get("grouped_departures", {})
        departures = grouped.get(self._line_key, [])

        if not departures:
            return "Aucun"

        dep = departures[0]
        if dep.waiting_time_minutes <= 0:
            return "Imminent"
        elif dep.waiting_time_minutes == 1:
            return "1 min"
        else:
            return f"{dep.waiting_time_minutes} min"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Retourner les attributs supplémentaires."""
        if not self.coordinator.data:
            return {}

        grouped = self.coordinator.data.get("grouped_departures", {})
        departures = grouped.get(self._line_key, [])

        attrs: dict[str, Any] = {
            ATTR_STOP_NAME: self._stop_name,
            ATTR_LINE: self._line,
            ATTR_DESTINATION: self._direction,
        }

        # Prochains départs pour cette ligne
        next_deps = []
        for dep in departures[:3]:
            dep_info = {
                "waiting_time": dep.waiting_time_minutes,
                "realtime": dep.realtime,
            }
            if dep.expected_arrival:
                dep_info["expected_time"] = dep.expected_arrival.isoformat()
            next_deps.append(dep_info)
        attrs[ATTR_NEXT_DEPARTURES] = next_deps

        if departures:
            attrs[ATTR_WAITING_TIME] = departures[0].waiting_time_minutes
            attrs[ATTR_REALTIME] = departures[0].realtime

        return attrs

    @property
    def icon(self) -> str:
        """Retourner l'icône basée sur le type de ligne."""
        line = self._line.upper()
        if line in ("A", "B", "C", "D", "01", "02", "03", "04"):
            return "mdi:tram"
        if "BAT" in line:
            return "mdi:ferry"
        return "mdi:bus"
