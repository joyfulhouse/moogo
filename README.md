# Moogo Smart Mosquito Misting Device for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

[![Project Maintenance][maintenance-shield]][user_profile]

A Home Assistant custom integration for Moogo smart mosquito misting devices, providing comprehensive device control, monitoring, and automation capabilities for automated mosquito control in your outdoor spaces.

## ⚡ Features

- 🏠 **Complete Home Assistant Integration** - Native support with proper device discovery
- 🦟 **Mosquito Control Monitoring** - Real-time misting device status, solution levels, environmental conditions
- 🎮 **Misting Device Control** - Start/stop mosquito misting operations with switch entities
- 📅 **Automated Schedule Management** - Monitor active misting schedules and next operation times
- 🌡️ **Environmental Sensors** - Temperature, humidity, and signal strength monitoring for optimal misting conditions
- 💧 **Solution Level Monitoring** - Mosquito control concentrate and water tank status ("OK" or "Empty")
- 🔄 **Smart Automation** - 30-second polling for real-time monitoring of your mosquito-free zone
- 🔐 **Secure Authentication** - Email/password authentication with token management
- 📶 **Public Data Access** - Access concentrate types and recommended misting schedules without authentication
- ⚡ **Device Management** - Firmware version tracking and comprehensive device information

## 🏗️ Supported Entities

### Sensors

**Public Data (Always Available):**
- **API Status** - Integration connectivity status
- **Concentrate Types** - Available mosquito control concentrate types with details
- **Schedule Templates** - Recommended mosquito misting schedule templates

**Authenticated Device Data:**
- **Device Status** - Online/offline status monitoring
- **Concentrate Level** - Mosquito control solution status ("OK" or "Empty")
- **Water Level** - Water tank status for misting system ("OK" or "Empty")
- **Temperature** - Environmental temperature readings (°C) for optimal misting conditions
- **Humidity** - Environmental humidity readings (%) affecting mosquito activity
- **Signal Strength** - Device WiFi signal strength (dBm)
- **Active Schedules** - Count of enabled mosquito misting schedules
- **Last Misting** - Timestamp and duration of most recent mosquito control misting

### Switches

- **Mosquito Misting Control** - Start/stop mosquito misting operations for each device

## 📦 Installation

### HACS *(Recommended)*

This integration includes HACS support and can be submitted to the HACS community store:

1. **Add Custom Repository** (until officially added):
   - Go to HACS → Integrations
   - Click the three dots menu → Custom repositories
   - Add repository URL: `https://github.com/joyfulhouse/moogo`
   - Category: Integration
   
2. **Install via HACS**:
   - Search for "Moogo Smart Mosquito Misting Device"
   - Click Install
   - Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases][releases]
2. Extract the files to your Home Assistant `custom_components` directory:
   ```
   /config/custom_components/moogo/
   ```
3. Restart Home Assistant
4. Add the integration through the UI: **Settings** → **Devices & Services** → **Add Integration** → **Moogo Smart Mosquito Misting Device**

### Direct Download

```bash
cd /config/custom_components
git clone https://github.com/joyfulhouse/moogo.git moogo
```

## ⚙️ Configuration

The integration supports two modes:

### 🔐 Full Access (Recommended)
Provide your Moogo account credentials for complete mosquito misting device control:
- All sensor data including device status, concentrate/water levels, environmental conditions
- Misting device control switches for mosquito control operations
- Real-time status updates every 30 seconds
- Device information including firmware version and misting history

### 📊 Public Data Only
Leave credentials blank to access:
- Available mosquito control concentrate types
- Recommended mosquito misting schedules
- Basic API connectivity status
- Updates every hour for public data

### Configuration Steps

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration** 
3. Search for **Moogo Smart Mosquito Misting Device** and select it
4. Choose your configuration:
   - **Full Access**: Enter your Moogo email and password
   - **Public Data**: Leave email and password fields empty
5. Click **Submit** to complete setup

## 🎯 Usage

### Automation Examples

**Low Level Alert:**
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
          message: "Mosquito control concentrate is empty - please refill for continued protection"

  - alias: "Moogo Low Water Alert" 
    trigger:
      - platform: state
        entity_id: sensor.moogo_s1_yitg_water_level
        to: "Empty"
    action:
      - service: notify.mobile_app
        data:
          title: "Moogo Mosquito Control Alert"
          message: "Misting system water level is empty - please refill for continued operation"
```

**Evening Mosquito Control:**
```yaml
automation:
  - alias: "Evening Mosquito Misting Schedule"
    trigger:
      platform: time
      at: "19:00:00"  # Peak mosquito activity time
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
        data:
          # Start mosquito misting for outdoor protection
```

**Temperature-Based Mosquito Control:**
```yaml
automation:
  - alias: "Hot Weather Mosquito Misting"
    trigger:
      - platform: numeric_state
        entity_id: sensor.moogo_s1_yitg_temperature
        above: 25  # Optimal temperature for mosquito activity
    condition:
      - condition: state
        entity_id: sensor.moogo_s1_yitg_status
        state: "Online"
      - condition: time
        after: "18:00:00"  # Evening hours when mosquitoes are most active
        before: "22:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.moogo_s1_yitg_spray
        data:
          # Activate misting when conditions favor mosquito activity
```

### Lovelace Card Example

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

## 🔧 Troubleshooting

### Common Issues

**Integration not appearing**
- Ensure files are in `/config/custom_components/moogo/`
- Restart Home Assistant completely
- Check the logs for any error messages

**Authentication failures**
- Verify your Moogo account credentials
- Ensure your account has device access
- Check for rate limiting (24-hour lockout after multiple failed attempts)
- Try the public data mode first to test connectivity

**No device data**
- Confirm your devices are online in the Moogo mobile app
- Check if your account has the necessary permissions
- Review the integration logs for API errors

**Sensors not updating**
- Check your internet connection
- Verify the Moogo API service status
- Review coordinator update intervals in logs

**Sensors showing "Unknown"**
- Device may be offline - check device status sensor
- API may be temporarily unavailable
- Check integration logs for specific error messages

### Debug Logging

Add the following to your `configuration.yaml` for detailed logs:

```yaml
logger:
  default: info
  logs:
    custom_components.moogo: debug
    custom_components.moogo.moogo_api.client: debug
    custom_components.moogo.coordinator: debug
```

## 🛠️ Technical Details

### Requirements

- Home Assistant 2023.1 or later
- Python 3.11 or later
- Active internet connection
- Moogo account (optional, for full functionality)

### Architecture

This integration follows Home Assistant's development standards and uses:

- **DataUpdateCoordinator** for efficient API calls with smart polling intervals
- **Config Flow** for user-friendly setup supporting both authentication modes
- **Device Registry** integration for proper device management with firmware info
- **Async/await** patterns for non-blocking operations
- **Comprehensive error handling** for API failures and rate limiting

### API Information

The integration communicates with:
- **Production**: `https://api.moogo.com/`
- **Authentication**: Token-based with automatic refresh
- **Rate Limiting**: 24-hour lockout protection after multiple failed attempts
- **Update Intervals**: 30 seconds for real-time mosquito control monitoring, 1 hour for public data

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 🐛 [Report Issues][issues]
- 💬 [GitHub Discussions][discussions]  
- ❓ [Home Assistant Community Forum](https://community.home-assistant.io/)

## 🙏 Acknowledgments

This integration was developed by analyzing the excellent [Thermacell LIV integration](https://github.com/joyfulhouse/thermacell_liv) for structural patterns and best practices.

## ⚠️ Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by Moogo. All product names, logos, and brands are property of their respective owners.

---

**Moogo** and related trademarks are property of their respective owners. This integration is developed independently and is not endorsed by the trademark holders.

[releases-shield]: https://img.shields.io/github/release/joyfulhouse/moogo.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/joyfulhouse/moogo.svg?style=for-the-badge
[commits]: https://github.com/joyfulhouse/moogo/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/joyfulhouse/moogo.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Bryan%20Li%20%40btli-blue.svg?style=for-the-badge
[releases]: https://github.com/joyfulhouse/moogo/releases
[user_profile]: https://github.com/btli
[issues]: https://github.com/joyfulhouse/moogo/issues
[discussions]: https://github.com/joyfulhouse/moogo/discussions