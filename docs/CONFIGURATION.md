# Configuration

Full configuration reference for Moogo Smart Mosquito Misting Device.

## Adding the Integration

1. Go to **Settings → Devices & Services**.
2. Click **+ Add Integration**.
3. Search for **Moogo Smart Mosquito Misting Device** and select it.
4. Choose a mode (see below) and submit.

## Configuration Options

| Option | Description | Default |
|---|---|---|
| Email | Moogo account email address | _(blank = public data only)_ |
| Password | Moogo account password | _(blank = public data only)_ |

**Full Access mode** (email + password provided):
- All device sensors and control switches
- 30-second polling interval

**Public Data Only mode** (credentials left blank):
- Concentrate types, schedule templates, and API status sensors
- 1-hour polling interval

## Reconfiguration

To switch between modes or update credentials, remove and re-add the integration
via **Settings → Devices & Services → Moogo → Delete**, then add it again.

## Advanced Options

- **Polling interval**: 30 seconds for authenticated data; 1 hour for public data. Not user-configurable.
- **Debug logging**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#enabling-debug-logging).
- **Rate limiting**: After multiple failed logins the Moogo API imposes a 24-hour lockout (error code `10000`). The integration surfaces this as a setup error.
