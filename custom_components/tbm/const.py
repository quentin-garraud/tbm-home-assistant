"""Constantes pour l'intégration TBM."""
from typing import Final

DOMAIN: Final = "tbm"

# Configuration
CONF_STOP_ID: Final = "stop_id"
CONF_STOP_NAME: Final = "stop_name"
CONF_LINE_ID: Final = "line_id"
CONF_DIRECTION: Final = "direction"

# Valeurs par défaut
DEFAULT_SCAN_INTERVAL: Final = 60  # secondes

# API TBM
TBM_API_BASE_URL: Final = "https://ws.infotbm.com/ws/1.0"
TBM_API_STOPS_URL: Final = f"{TBM_API_BASE_URL}/network/stoparea-informations"
TBM_API_SCHEDULES_URL: Final = f"{TBM_API_BASE_URL}/get-realtime-pass"

# Attributs
ATTR_STOP_NAME: Final = "stop_name"
ATTR_LINE: Final = "line"
ATTR_DIRECTION: Final = "direction"
ATTR_DESTINATION: Final = "destination"
ATTR_DEPARTURE_TIME: Final = "departure_time"
ATTR_WAITING_TIME: Final = "waiting_time"
ATTR_NEXT_DEPARTURES: Final = "next_departures"
ATTR_VEHICLE_TYPE: Final = "vehicle_type"
ATTR_REALTIME: Final = "realtime"

