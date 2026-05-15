# SMD D-KEYS

Home Assistant custom integration for SMD / D-KEYS intercom accounts.

## What This Does

- Authenticates with the same phone + call-code flow used by the Android app.
- Discovers the account's available doors.
- Lets you choose which doors become Home Assistant entities.
- Sends the reverse-engineered SMD open-door command.
- Exposes live RTSP intercom video as Home Assistant `camera` entities when SMD advertises video for the selected door.
- Starts Home Assistant reauthentication when SMD rejects the saved token.

The lock state is assumed. After a successful open command, the entity reports unlocked for the configured relock delay and then returns to locked. It is not a physical door contact or magnetic lock sensor.

## Installation

### HACS

1. Open HACS.
2. Open three-dot menu > Custom repositories.
3. Add this repository URL with category `Integration`.
4. Install `SMD D-KEYS`.
5. Restart Home Assistant.
6. Add the integration from Settings > Devices & services.

This repository is HACS-ready through `hacs.json`, `custom_components/smd_d_keys/manifest.json`, bundled brand assets, and the validation workflow in `.github/workflows/validate.yaml`.

### Local Test Home Assistant

For fast local testing, run Home Assistant with Docker Compose from the repository root:

```bash
docker compose up -d
```

Open `http://localhost:8123`, complete the first-run wizard, then add `SMD D-KEYS` from Settings > Devices & services.

The compose setup mounts:

- `./custom_components/smd_d_keys` into Home Assistant as a read-only custom integration.
- `./.local/homeassistant/config` as the local Home Assistant config directory.

Local Home Assistant runtime files under `.local/` are ignored by git.

Useful commands:

```bash
docker compose logs -f homeassistant
docker compose restart homeassistant
docker compose down
```

### Development Checks

Run the same local checks expected before pushing:

```bash
uv run poe validate
```

This runs formatting, linting, tests, and hassfest. To run only hassfest:

```bash
uv run poe hassfest
```

### Manual

Copy `custom_components/smd_d_keys` into your Home Assistant `custom_components` directory and restart Home Assistant.

## Configuration

1. Enter the phone number used in the D-KEYS app.
2. SMD will call your phone. Enter the last 6 digits of the caller number.
3. Select the doors to expose in Home Assistant.

Manual token entry is intentionally not supported.

## Options

- `Doors`: which discovered doors should have lock/camera entities.
- `Assumed relock delay`: seconds before the entity returns to locked after a successful open command.

## Camera Support

Live camera support uses the Android app's account-level `getVideo` and `getVideoBroadcastByProtocol` flow. The integration returns an RTSP source to Home Assistant; Home Assistant's stream stack and go2rtc can then restream it for dashboards and companion apps.

The current MVP is live-stream-only. Still images and thumbnails are not fetched from SMD yet.

Archive playback, incoming video calls, WebRTC handling, and push-event handling are intentionally left for later iterations.

## Troubleshooting

If the SMD token expires or is revoked, Home Assistant starts the integration reauthentication flow. Enter the phone number and call code again; selected doors and options are preserved.

Diagnostics redact tokens, phone numbers, account IDs, selected door IDs, and command server URLs.

## Reverse-Engineering Notes

Sanitized APK/API notes are in `docs/research/`. Binary APK/XAPK files, decompiled output, captured traffic, tokens, phone numbers, addresses, and real door identifiers must stay out of git.
