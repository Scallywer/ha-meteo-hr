"""Constants for the Meteo.hr weather integration."""

DOMAIN = "meteo_hr"

CONF_CITY_CODE = "city_code"
CONF_STATION_NAME = "station_name"

DEFAULT_CITY_CODE = "OSIJEK"
DEFAULT_STATION_NAME = "Osijek"
DEFAULT_NAME = "Meteo.hr"

FORECAST_URL = "https://meteo.hr/7d_graf_i_simboli.xml"
SYMBOLS_URL = "https://meteo.hr/assets/jsi/prognoze_OpisiSimbola.json"

# HTML page whose <select id="menprog"> lists every valid forecast city code.
CITY_LIST_URL = "https://meteo.hr/prognoze.php?section=prognoze_model&param=7d"

# Real station observations (current conditions) and hourly UV index tables.
CONDITIONS_URL = "https://meteo.hr/podaci.php?section=podaci_vrijeme&param=hrvatska1_n"
UV_INDEX_URL = "https://meteo.hr/podaci.php?section=podaci_vrijeme&param=uvi"

UPDATE_INTERVAL_MINUTES = 60
OBSERVATIONS_UPDATE_INTERVAL_MINUTES = 30
