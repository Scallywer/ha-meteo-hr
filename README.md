# Meteo.hr Weather for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

**Status: beta.** Working end-to-end, but new — expect rough edges, and version numbers below 1.0 mean the config/entity shape may still change.

A native Home Assistant `weather` integration backed by [DHMZ](https://meteo.hr) (the Croatian Meteorological and Hydrological Service) forecast data, via the public `meteo.hr` website.

Croatia isn't covered particularly well by the weather providers Home Assistant ships with (Met.no, OpenWeatherMap, AccuWeather, etc.) — DHMZ's own model is the most locally accurate source available, but there was no way to pull it into HA as a first-class `weather.*` entity. This integration does that: a real weather entity with current conditions, daily forecast, and hourly forecast, usable with the built-in weather card, `weather.get_forecasts`, and any weather-consuming automation or Lovelace card.

## Features

- Native `weather.*` entity — works with the stock Home Assistant weather card, no custom Lovelace card required
- Current condition, temperature, wind speed/bearing
- 7-day daily forecast (high/low, precipitation total, precipitation probability, condition)
- Multi-day hourly forecast (temperature, condition, wind, precipitation, precipitation probability)
- **Real station observations** (separate from the forecast, added in 0.2.0): current temperature, wind, and sky condition from an actual weather station reading, plus hourly UV index — both refreshed every 30 minutes on their own independent schedule
- Any city/location covered by DHMZ's forecast model — not just the state capitals
- No API key required

## Data source

Data comes from the same feed that powers the 7-day forecast graph on [meteo.hr](https://meteo.hr/prognoze.php?section=prognoze_model&param=7d) — DHMZ's public forecast model output. This integration fetches and parses that feed directly; it does not scrape rendered HTML or images, so it's resilient to page redesigns as long as the underlying feed stays in place. Refreshed hourly.

Weather condition text (Croatian) is mapped to Home Assistant's standard condition set (`sunny`, `partlycloudy`, `cloudy`, `rainy`, `pouring`, `lightning`, `lightning-rainy`, `snowy`, `snowy-rainy`, `fog`, `clear-night`) via keyword matching against DHMZ's own symbol descriptions, so it stays correct even if DHMZ adds new symbol codes.

The observation sensors come from two different pages — DHMZ's [current-conditions table](https://meteo.hr/podaci.php?section=podaci_vrijeme&param=hrvatska1_n) and [UV index table](https://meteo.hr/podaci.php?section=podaci_vrijeme&param=uvi) — parsed with a small dependency-free HTML table reader (`scrape.py`), not a full HTML parser library.

## Installation

### HACS (recommended)

Not yet in the HACS default store — add it as a custom repository for now:

1. In HACS, go to **Integrations → ⋮ → Custom repositories**, add `https://github.com/Scallywer/ha-meteo-hr` as category **Integration**.
2. Search for **Meteo.hr Weather** in HACS and install it.
3. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**, search for **Meteo.hr Weather**.

### Manual

1. Copy `custom_components/meteo_hr` into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**, search for **Meteo.hr Weather**.

## Configuration

Configuration is done entirely through the UI (no YAML). Both fields are live dropdowns — populated at setup time from meteo.hr's own option lists, not free text:

| Field | Description |
|---|---|
| Name | Friendly name for the resulting entities |
| City | Forecast source (`weather.*` entity) — DHMZ's full location list, e.g. Osijek, Zagreb-Maksimir, Split-Marjan, Rijeka, Pula, Dubrovnik |
| Station | Real-observation source (temperature/wind/UV sensors) — **a different, smaller list than City**. The current-conditions and UV-index pages don't share a consistent station list (some coastal towns have UV data but no full weather station, or vice versa), so this dropdown only offers stations present in *both* sources — whatever you pick is guaranteed to populate all the observation sensors. |

You can add the integration multiple times with different cities/stations to cover more than one location.

## Limitations

- The `weather.*` entity is forecast-model data, not a live reading — its "current" conditions are the nearest forecast hour to now, not a real-time station measurement. (The separate observation sensors *are* real station readings, refreshed every 30 minutes — see Features above.)
- Humidity, pressure, and visibility aren't part of either the forecast feed or the observation sensors, so those attributes aren't populated anywhere.
- The forecast model's time resolution decreases for days further out (hourly for the first few days, sparser toward day 7), which DHMZ's own feed reflects — this integration doesn't invent additional resolution.
- The UV index sensor only has values for daylight hours the station has already reported — it reads as the most recent hour available, not necessarily the current clock hour.

## Credits

Weather data © [DHMZ](https://meteo.hr) (Državni hidrometeorološki zavod / Croatian Meteorological and Hydrological Service). This project is not affiliated with or endorsed by DHMZ.
