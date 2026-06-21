# Changelog

## NightScope RC1 - 2026-06-21

- Added rotating application logging in `logs/nightscope.log`.
- Hardened SQLite bootstrap with integrity checks, automatic backup, corrupt database quarantine and rebuild.
- Hardened Open-Meteo handling for timeout, unreachable API, empty payloads, malformed JSON and rate limiting.
- Hardened Skyfield ephemeris loading with controlled failure and fallback through the app controller.
- Added loading, empty and error states to Home and Meteo screens.
- Added astronomy validation tests for Addis Ababa, Roma, Milano, Cape Town and Oslo.
- Added timezone/DST validation tests for Europe/Rome.
- Added release scenario tests for online forecast, offline weather and unavailable Windows Location.
- Added generated astronomy validation report.
- Added PyInstaller Windows packaging spec, build script and application icon.
