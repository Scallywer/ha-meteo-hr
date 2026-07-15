# Changelog

All notable changes to this project are documented here.

## [0.2.1] - 2026-07-15

### Fixed

- `manifest.json` keys weren't in the order hassfest requires (`domain`, `name`, then alphabetical) — was failing CI validation on every push.
- Added a self-served brand icon (`custom_components/meteo_hr/brand/icon.png` + `icon@2x.png`), using HA 2026.3's local brand-asset support — no `home-assistant/brands` submission needed.

No functional changes to the integration itself.

## [0.2.0] - 2026-07-15

### Added

- Real station observation sensors: current temperature, wind, and sky condition from an actual weather station reading, plus hourly UV index — both refreshed every 30 minutes on their own independent schedule, separate from the forecast entity.

## [0.1.0] - 2026-07-15

### Added

- Initial release: a native Home Assistant `weather.*` entity backed by DHMZ's (meteo.hr) public 7-day hourly forecast feed.
- Current condition, temperature, wind speed/bearing.
- 7-day daily forecast and multi-day hourly forecast.
- Config-flow setup with live City dropdown populated from meteo.hr's own location list — no YAML.
