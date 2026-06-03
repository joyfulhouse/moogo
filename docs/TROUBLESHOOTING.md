# Troubleshooting

Common problems with Moogo Smart Mosquito Misting Device and how to resolve them.

## Common Issues

### Integration not appearing after install

- Confirm files are in `config/custom_components/moogo/`.
- Restart Home Assistant completely (not just reload).
- Check Home Assistant logs for import errors.

### Authentication failures (error code 10104)

- Verify your Moogo email and password are correct.
- Ensure your account has device access in the Moogo mobile app.
- Try the public-data-only mode first to confirm API connectivity.

### Rate-limited lockout (error code 10000)

- The Moogo API locks accounts for 24 hours after repeated failed login attempts.
- Wait 24 hours before retrying credentials.
- Use public-data-only mode in the interim.

### No device data / sensors show "Unknown"

- Confirm your devices are online in the Moogo mobile app.
- Check the Device Status sensor — if "Offline", the device itself is unreachable.
- Review coordinator logs for API errors.

### Sensors not updating

- Check your internet connection.
- Verify the Moogo API is reachable (`https://api.moogo.com/`).
- Enable debug logging and inspect coordinator update intervals.

## Enabling Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.moogo: debug
    custom_components.moogo.coordinator: debug
```

Restart Home Assistant and reproduce the issue. Logs appear under **Settings → System → Logs**.

## Getting Help

If you are still stuck, open an issue at
<https://github.com/joyfulhouse/moogo/issues> with logs and reproduction
steps.
