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
- Any city/location covered by DHMZ's forecast model — not just the state capitals
- No API key required

## Data source

Data comes from the same feed that powers the 7-day forecast graph on [meteo.hr](https://meteo.hr/prognoze.php?section=prognoze_model&param=7d) — DHMZ's public forecast model output. This integration fetches and parses that feed directly; it does not scrape rendered HTML or images, so it's resilient to page redesigns as long as the underlying feed stays in place. Refreshed hourly.

Weather condition text (Croatian) is mapped to Home Assistant's standard condition set (`sunny`, `partlycloudy`, `cloudy`, `rainy`, `pouring`, `lightning`, `lightning-rainy`, `snowy`, `snowy-rainy`, `fog`, `clear-night`) via keyword matching against DHMZ's own symbol descriptions, so it stays correct even if DHMZ adds new symbol codes.

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

Configuration is done entirely through the UI (no YAML):

| Field | Description |
|---|---|
| Name | Friendly name for the resulting `weather.*` entity |
| City code | The DHMZ location code, e.g. `OSIJEK`, `ZAGREB-MAKSIMIR`, `SPLIT-MARJAN`, `RIJEKA`, `PULA`, `DUBROVNIK` |

City codes match the options in the location dropdown on the [meteo.hr forecast page](https://meteo.hr/prognoze.php?section=prognoze_model&param=7d) — use the same spelling/formatting shown there (spaces and diacritics included where the source uses them).

You can add the integration multiple times with different city codes to get weather entities for more than one location.

## Limitations

- This is forecast-model data, not live station observations — "current" conditions are the nearest forecast hour to now, not a real-time sensor reading.
- Humidity, pressure, and visibility aren't part of the underlying feed, so those attributes aren't populated.
- The forecast model's time resolution decreases for days further out (hourly for the first few days, sparser toward day 7), which DHMZ's own feed reflects — this integration doesn't invent additional resolution.

## Credits

Weather data © [DHMZ](https://meteo.hr) (Državni hidrometeorološki zavod / Croatian Meteorological and Hydrological Service). This project is not affiliated with or endorsed by DHMZ.
