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

# API TBM (SIRI Lite via Mecatran)
TBM_API_KEY: Final = "opendata-bordeaux-metropole-flux-gtfs-rt"
TBM_API_BASE_URL: Final = "https://bdx.mecatran.com/utw/ws/siri/2.0/bordeaux"
TBM_STOP_MONITORING_URL: Final = f"{TBM_API_BASE_URL}/stop-monitoring.json"
TBM_STOPPOINTS_DISCOVERY_URL: Final = f"{TBM_API_BASE_URL}/stoppoints-discovery.json"
TBM_LINES_DISCOVERY_URL: Final = f"{TBM_API_BASE_URL}/lines-discovery.json"

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
ATTR_AIMED_TIME: Final = "aimed_time"
ATTR_EXPECTED_TIME: Final = "expected_time"
