# Architecture

How Moogo Smart Mosquito Misting Device is structured and why.

## Overview

This is a Home Assistant custom integration that polls the Moogo cloud REST API
(`https://api.moogo.com/`) to expose mosquito misting device state as HA entities.
All API interactions are delegated to the
[pymoogo](https://github.com/joyfulhouse/pymoogo) library.

## Components

| Module | Responsibility |
|---|---|
| `__init__.py` | Integration setup, entry point, coordinator wiring |
| `config_flow.py` | Config UI — email/password or public-data-only mode |
| `coordinator.py` | `DataUpdateCoordinator` — fetches data every 30 s (auth) or 1 h (public) |
| `sensor.py` | Sensor entities: status, levels, temperature, humidity, signal, schedules |
| `switch.py` | Switch entities: start/stop misting per device |
| `const.py` | Constants: API endpoints, update intervals, entity keys |
| `strings.json` | UI translations and error messages |
| `moogo_api/` | Bundled legacy client (superseded by pymoogo in v2) |

## Data Flow

1. HA calls the coordinator on its update interval.
2. The coordinator calls `pymoogo` to fetch device list and per-device status.
3. Sensor and switch entities read state from the coordinator's cached data.
4. Control commands (start/stop) are sent directly via `pymoogo` and trigger a coordinator refresh.

## Key Design Decisions

- **Two-mode config flow**: unauthenticated access for public data (concentrate types, schedule templates) avoids requiring credentials for basic use.
- **DataUpdateCoordinator**: single polling point avoids redundant API calls across entities.
- **pymoogo delegation**: API client lives in a separate library for testability and reuse.
- **Rate-limit handling**: 24-hour lockout (`code 10000`) is surfaced as a config error to prevent repeated failed logins.
