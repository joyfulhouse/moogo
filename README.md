# Moogo Smart Mosquito Misting Device

A Home Assistant custom integration for Moogo smart mosquito misting devices, providing device control, monitoring, and automation for automated mosquito management in outdoor spaces.

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![HACS][hacs-shield]][hacs]
[![CI][ci-shield]][ci]
[![Project Maintenance][maintenance-shield]][maintenance]
[![GitHub Sponsors][sponsors-shield]][sponsors]
[![Ko-fi][kofi-shield]][kofi]

## What It Does

This integration connects Home Assistant to Moogo cloud-connected mosquito misting devices via the Moogo REST API (`https://api.moogo.com/`). It supports both authenticated (full device control) and unauthenticated (public data) modes. Entities update every 30 seconds for authenticated device data and every hour for public data.

## Features

- Start/stop mosquito misting operations via switch entities
- Real-time device status: online/offline, concentrate level, water level
- Environmental sensors: temperature (°C), humidity (%), WiFi signal strength (dBm)
- Active schedule count and last misting timestamp per device
- Public data access: available concentrate types and recommended schedule templates
- Config flow supporting both full-access (email/password) and public-data-only modes
- 24-hour rate-limit detection and management for failed login attempts
- Automatic token refresh and session persistence

## Prerequisites

- Home Assistant 2023.1.0 or newer
- [HACS](https://hacs.xyz) installed (recommended for installation)
- A Moogo account (optional — required only for device control and per-device sensors)
- Active internet connection (cloud-polling integration)

## Installation

See **[INSTALL.md](INSTALL.md)** for the complete guide.

**Quick version (HACS):** add this repository as a custom repository in HACS,
install **Moogo Smart Mosquito Misting Device**, restart Home Assistant, then add the integration
from **Settings → Devices & Services**.

[![Open in HACS][hacs-repo-shield]][hacs-repo]

## Configuration

The integration supports two modes:

**Full Access (Recommended)** — provide your Moogo email and password:

- All device sensors (status, levels, temperature, humidity, signal strength)
- Misting control switch per device
- Real-time updates every 30 seconds

**Public Data Only** — leave credentials blank:

- Concentrate types and recommended schedule templates
- API connectivity status sensor
- Updates every hour

### Configuration Steps

1. Go to **Settings → Devices & Services**
2. Click **Add Integration** and search for **Moogo Smart Mosquito Misting Device**
3. Enter your Moogo email and password for full access, or leave blank for public data only
4. Click **Submit**

## Supported Equipment

Any Moogo smart mosquito misting device registered to your account. Entities are created per device.

### Sensors

| Entity | Description | Mode |
|---|---|---|
| API Status | Integration connectivity | Public |
| Concentrate Types | Available concentrate types with details | Public |
| Schedule Templates | Recommended misting schedule templates | Public |
| Device Status | Online/offline | Authenticated |
| Concentrate Level | Mosquito control solution status ("OK" / "Empty") | Authenticated |
| Water Level | Water tank status ("OK" / "Empty") | Authenticated |
| Temperature | Environmental temperature (°C) | Authenticated |
| Humidity | Environmental humidity (%) | Authenticated |
| Signal Strength | WiFi signal strength (dBm) | Authenticated |
| Active Schedules | Count of enabled misting schedules | Authenticated |
| Last Misting | Timestamp and duration of most recent operation | Authenticated |

### Switches

| Entity | Description |
|---|---|
| Mosquito Misting Control | Start/stop misting for each device |

## Automation Examples

**Low concentrate alert:**

```yaml
automation:
  - alias: "Moogo Low Concentrate Alert"
    trigger:
      - platform: state
        entity_id: sensor.moogo_s1_yitg_liquid_level
        to: "Empty"
    action:
      - service: notify.mobile_app
        data:
          title: "Moogo Mosquito Control Alert"
          message: "Mosquito control concentrate is empty - please refill"
```

**Evening misting when device is online and supplies are adequate:**

```yaml
automation:
  - alias: "Evening Mosquito Misting Schedule"
    trigger:
      platform: time
      at: "19:00:00"
    condition:
      - condition: state
        entity_id: sensor.moogo_s1_yitg_status
        state: "Online"
      - condition: state
        entity_id: sensor.moogo_s1_yitg_liquid_level
        state: "OK"
      - condition: state
        entity_id: sensor.moogo_s1_yitg_water_level
        state: "OK"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.moogo_s1_yitg_spray
```

**Temperature-triggered misting during peak mosquito hours:**

```yaml
automation:
  - alias: "Hot Weather Mosquito Misting"
    trigger:
      - platform: numeric_state
        entity_id: sensor.moogo_s1_yitg_temperature
        above: 25
    condition:
      - condition: state
        entity_id: sensor.moogo_s1_yitg_status
        state: "Online"
      - condition: time
        after: "18:00:00"
        before: "22:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.moogo_s1_yitg_spray
```

**Lovelace card:**

```yaml
type: entities
title: Moogo Mosquito Misting System
entities:
  - entity: sensor.moogo_s1_yitg_status
    name: Device Status
  - entity: sensor.moogo_s1_yitg_liquid_level
    name: Concentrate Level
  - entity: sensor.moogo_s1_yitg_water_level
    name: Water Level
  - entity: sensor.moogo_s1_yitg_temperature
    name: Temperature
  - entity: sensor.moogo_s1_yitg_humidity
    name: Humidity
  - entity: sensor.moogo_s1_yitg_signal_strength
    name: Signal Strength
  - entity: sensor.moogo_s1_yitg_active_schedules
    name: Active Misting Schedules
  - entity: sensor.moogo_s1_yitg_last_spray
    name: Last Misting
  - entity: switch.moogo_s1_yitg_spray
    name: Mosquito Misting Control
```

## Troubleshooting

**Integration not appearing**
- Ensure files are in `config/custom_components/moogo/`
- Restart Home Assistant completely
- Check Home Assistant logs for error messages

**Authentication failures**
- Verify your Moogo account credentials
- Ensure your account has device access
- Rate limiting applies a 24-hour lockout after multiple failed attempts; try public data mode to verify connectivity
- Check for `10104` (invalid credentials) or `10000` (rate-limited) in logs

**No device data**
- Confirm your devices are online in the Moogo mobile app
- Check that your account has the necessary permissions
- Review integration logs for API errors

**Sensors not updating or showing "Unknown"**
- Check your internet connection
- Device may be offline — check the device status sensor
- Review coordinator update intervals in logs; add debug logging (see below)

**Debug logging:**

```yaml
logger:
  default: info
  logs:
    custom_components.moogo: debug
    custom_components.moogo.coordinator: debug
```

## Development

This integration is built on the
[pymoogo](https://github.com/joyfulhouse/pymoogo) Python
library. See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) to set up a development
environment.

## Support

- **Issues:** <https://github.com/joyfulhouse/moogo/issues>
- **Discussions / questions:** open an issue with the `question` label.

## Support Development

If this project is useful to you, please consider supporting its development:

- [GitHub Sponsors][sponsors]
- [Ko-fi][kofi]

## License

This project is licensed under the **MIT** License — see
[LICENSE](LICENSE) for details.

## Credits

Built and maintained by [JoyfulHouse](https://github.com/joyfulhouse) with the
[pymoogo](https://github.com/joyfulhouse/pymoogo) library.

This is an unofficial integration and is not affiliated with or endorsed by Moogo.

<!-- Badge links -->
[releases-shield]: https://img.shields.io/github/release/joyfulhouse/moogo.svg?style=for-the-badge
[releases]: https://github.com/joyfulhouse/moogo/releases
[license-shield]: https://img.shields.io/github/license/joyfulhouse/moogo.svg?style=for-the-badge
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacs-repo-shield]: https://my.home-assistant.io/badges/hacs_repository.svg
[hacs-repo]: https://my.home-assistant.io/redirect/hacs_repository/?owner=joyfulhouse&repository=moogo&category=integration
[ci-shield]: https://img.shields.io/github/actions/workflow/status/joyfulhouse/moogo/hacs-validate.yml?style=for-the-badge&label=CI
[ci]: https://github.com/joyfulhouse/moogo/actions
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40btli-blue.svg?style=for-the-badge
[maintenance]: https://github.com/btli
[sponsors-shield]: https://img.shields.io/badge/sponsor-GitHub-EA4AAA.svg?style=for-the-badge&logo=githubsponsors&logoColor=white
[sponsors]: https://github.com/sponsors/btli
[kofi-shield]: https://img.shields.io/badge/Ko--fi-donate-FF5E5B.svg?style=for-the-badge&logo=ko-fi&logoColor=white
[kofi]: https://ko-fi.com/bryanli
