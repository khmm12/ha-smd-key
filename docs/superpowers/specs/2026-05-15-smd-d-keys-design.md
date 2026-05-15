# SMD D-KEYS Home Assistant Integration Design

Date: 2026-05-15

## Goal

Build a HACS-ready Home Assistant custom integration for SMD / СтройМастерДомофон / D-KEYS that authenticates through the same phone + call-code flow as the official Android app and exposes selected intercom doors as Home Assistant `lock` entities.

The MVP must not require or accept manual token entry. It must obtain the token through the reverse-engineered authentication flow, discover the account's available doors, and let the user choose which doors to add.

## Confirmed Decisions

- Integration domain: `smd_d_keys`.
- Human-readable name: `SMD D-KEYS`.
- One Home Assistant config entry represents one SMD account.
- A single account may expose multiple doors/houses.
- MVP entity type: `lock` only.
- MVP must surface expired or revoked authentication as a Home Assistant Repairs issue with a reauth path.
- Camera, video streams, incoming calls, push events, and guest photos are out of MVP and belong in the roadmap after reverse-engineering.
- First implementation path is reverse-first: document the APK/API findings before writing the Home Assistant integration.
- No APK, XAPK, decompiled output, tokens, phone numbers, addresses, or other sensitive artifacts are committed to git.
- All commits must follow Conventional Commits.

## Current Evidence

### Existing PoC

The existing proof of concept is on `home-pi` at:

```text
~/services/smarthome/data/homeassistant/custom_components/smd_d_key/
```

Read-only reconnaissance found these files:

- `__init__.py`
- `config_flow.py`
- `const.py`
- `lock.py`
- `manifest.json`
- `smd_door_client.py`

The PoC creates one `lock` entity from manually entered `session_token` and `door_id`. It sends:

```text
POST http://mqapp.s-m-d.ru:47393/
action=openDoor
token=<session_token>
topic=<door_id>
text=cmd1
```

It treats `response_json["error"] == "false"` as success. After a successful open command it marks the lock locally unlocked, waits 5 seconds, then marks it locked again. This is an assumed UI state, not a real sensor state.

The new integration must preserve the useful fact that `openDoor` exists, but must replace manual token entry with real phone + call-code authentication.

## Authentication Contract

Authentication is a product requirement, not an agent workflow preference. The integration must authenticate through the reverse-engineered official app flow:

1. User enters the phone number used by the D-KEYS app.
2. SMD places an authentication call from a unique caller number.
3. User enters the last six digits of the caller number.
4. The integration sends that call code to the SMD API and stores the returned token in the Home Assistant config entry.
5. Reauthentication repeats the same phone + call-code flow and updates the existing config entry.

Manual token entry, pasted captured tokens, MITM-only setup, YAML token setup, or hidden token fallbacks are not acceptable setup paths. Captured tokens may be used only as temporary local reverse-engineering evidence outside git, never as a supported user-facing authentication mode.

### APK Sources Found

The Android package is `com.smd.ip_smd`, published as `D-KEYS` by `Платформа D-Keys`.

Known public references:

- Google Play: `https://play.google.com/store/apps/details?id=com.smd.ip_smd`
- APKCombo: `https://apkcombo.com/d-keys/com.smd.ip_smd`
- APKPure: `https://apkpure.com/ru/d-keys/com.smd.ip_smd/download/`

Observed public metadata during research:

- Package: `com.smd.ip_smd`
- App name: `D-KEYS`
- Recent versions observed: `5.3.x`
- APKPure/APKCombo list XAPK/APK builds, sizes around 80-85 MB for recent versions.

The implementation phase must record the exact downloaded version, source URL, download date, file size, SHA256, signing certificate fingerprint, architecture, and tool versions before using the APK for reverse-engineering.

## Research Documentation Requirements

Create and maintain `docs/research/` before and during implementation. The research docs are part of the deliverable, not scratch notes.

Required files:

- `docs/research/apk-sources.md`
- `docs/research/reverse-engineering.md`
- `docs/research/api.md`
- `docs/research/video-and-calls.md`
- `docs/research/poc-notes.md`

`apk-sources.md` must answer:

- Where the APK/XAPK was found.
- Which exact version and version code were downloaded.
- When it was downloaded.
- What file size and SHA256 were observed.
- Which signing certificate fingerprint was observed.
- Which architecture split was inspected.
- Which URLs should be checked again if a future maintainer needs a fresh APK.

`reverse-engineering.md` must answer:

- Which tools were used, such as `jadx`, `apktool`, `apksigner`, `bundletool`, or equivalent.
- Tool versions and install method.
- Exact commands used.
- Where temporary binary/decompiled artifacts were stored outside git.
- Which packages/classes/resources/strings were relevant.
- Which findings are confirmed and which are inferred.

`api.md` must answer:

- How phone + call-code authentication works.
- Token fields, storage shape, expiration behavior, and refresh or reauth behavior.
- How available houses/doors are listed.
- How a door is opened.
- Required headers, content type, user-agent behavior, timeout expectations, response schema, and error schema.
- Rate limits or retry behavior if discovered.

`video-and-calls.md` must collect non-MVP findings:

- Camera stream endpoints and protocol.
- Incoming call signaling.
- Push notification flow.
- Guest photo flow.
- Any blockers for a future Home Assistant `camera` or event platform.

`poc-notes.md` must document:

- The PoC path on `home-pi`.
- The old manual-token model.
- The old `openDoor` request shape.
- Why manual token setup is rejected for the new MVP.
- Differences between PoC behavior and the new design.

## Home Assistant Architecture

Repository structure:

```text
custom_components/smd_d_keys/
tests/
docs/research/
docs/superpowers/specs/
README.md
ROADMAP.md
hacs.json
pyproject.toml
```

The integration follows modern Home Assistant custom integration patterns:

- `async_setup_entry` and `async_unload_entry`.
- Platforms loaded via `async_forward_entry_setups`.
- Runtime objects stored in typed `entry.runtime_data`, not `hass.data`.
- HTTP handled with Home Assistant's shared `aiohttp` session from `async_get_clientsession`.
- No synchronous `requests`.
- No naive `datetime.now()`.
- Entity attributes must remain JSON-serializable.
- Credentials and PII must never be logged.

The initial platform list contains only:

- `lock`

The integration should use a small typed API layer with separate exception classes for:

- authentication failure
- network/connectivity failure
- API response failure
- rate limiting
- malformed response

Auth failures should become Home Assistant reauth flows. Transient network/API problems should surface as setup retry or entity availability failures as appropriate.

## Repairs And Reauthentication

Expired, revoked, or otherwise invalid SMD tokens are part of MVP behavior. They must not be handled only by logging an error or marking entities unavailable forever.

When the API layer detects an authentication failure after setup, the integration must raise `ConfigEntryAuthFailed` with the integration translation domain and a specific translation key. Home Assistant should then surface an actionable Repairs issue and route the user into the integration's reauth flow.

The reauth flow should:

1. Keep the existing config entry and selected doors.
2. Ask for the phone number only if the stored account identifier is insufficient or the user needs to change it.
3. Send a fresh authentication call request.
4. Accept the call code.
5. Exchange it for a new token/session.
6. Update the existing entry data.
7. Reload the entry.
8. Clear the auth repair state by completing the reauth flow successfully.

If reverse-engineering reveals non-auth account problems that need user action, such as an account without any active keys, blocked service, or removed address, the integration may create explicit issue-registry Repairs issues with translated titles/descriptions. These issue IDs must be stable per config entry and must not include phone numbers, addresses, tokens, or raw door IDs.

## Config Flow

The config flow is UI-only and has no YAML setup path.

Flow:

1. User enters phone number.
2. Integration sends an authentication call request through the reverse-engineered API.
3. User enters the call code.
4. Integration exchanges the call code for an authenticated token/session.
5. Integration fetches available doors/houses for that account.
6. User selects which doors to expose in Home Assistant.
7. Integration creates one config entry for the account.

Duplicate protection should use a stable account identifier returned by the API if available. If no explicit account ID exists, the normalized phone number may be used as the fallback unique ID, but it must not be exposed in logs.

Manual token entry is not part of the MVP and should not appear as a hidden fallback.

The same phone + call-code steps are reused by `async_step_reauth`. Reauth updates an existing entry rather than creating a duplicate account.

## Options Flow

Options flow allows:

- selecting or deselecting doors exposed as entities
- changing `relock_delay` in seconds

The default `relock_delay` is 5 seconds, matching the PoC's user-interface assumption. This delay does not claim to represent a real physical door sensor.

Changing options should reload the entry or otherwise update entities cleanly without requiring a Home Assistant restart.

## Lock Entity Behavior

Each selected door becomes a `lock` entity with a stable unique ID based on the SMD door identifier.

`async_unlock()` sends the reverse-engineered open-door command. After success:

- the entity temporarily reports unlocked
- the entity schedules a return to locked after `relock_delay`
- Home Assistant state is written immediately after both transitions

Unless reverse-engineering discovers a real SMD lock command, `async_lock()` must not call the API. For MVP it only resets the local assumed state to locked immediately, which is equivalent to saying "stop showing the recent open command as active". This behavior must be documented in README and tests so users do not mistake it for a physical lock command.

The entity must document that its state is assumed. It indicates the recent open command lifecycle, not a verified magnetic lock or door contact state.

## Security And Privacy

Never commit:

- APK/XAPK files
- decompiled APK output
- captured traffic containing credentials
- tokens
- phone numbers
- addresses
- door IDs tied to a real account
- guest photos or video URLs

Diagnostics must redact at least:

- token-like values
- phone numbers
- call codes
- account identifiers if they expose personal data
- addresses
- door topics/IDs if tied to a real address

Logs must not contain raw request bodies for auth/open-door calls.

## Tooling

Use modern Python tooling:

- `uv` for dependency and virtual environment workflow
- `ruff` for linting and formatting
- `pytest`
- `pytest-homeassistant-custom-component`

Reverse-engineering toolchain should be documented when installed or used. Current local PATH reconnaissance found `uv`, but did not find `apktool`, `jadx`, `jadx-gui`, `apksigner`, or `bundletool`.

## Tests

Required test coverage for MVP:

- config flow starts authentication call from phone number
- config flow handles invalid phone/call-code/API errors
- config flow prevents duplicate account setup
- config flow fetches doors and stores selected doors
- options flow updates selected doors
- options flow updates `relock_delay`
- setup succeeds with stored account data
- setup retries or fails clearly on network/API/auth errors
- reauth starts when auth failure is detected
- expired/revoked token errors raise `ConfigEntryAuthFailed` and expose a Home Assistant Repairs path
- successful reauth updates the existing entry without changing selected doors
- unload cleans up forwarded platforms and runtime data
- lock entities expose stable unique IDs and device info
- `async_unlock()` sends the correct API request
- successful unlock temporarily reports unlocked and returns to locked after delay
- failed unlock raises an appropriate Home Assistant error
- diagnostics redact credentials and personal data

Use mocked API responses for automated tests. Live account credentials provided by the user must not be committed and should be used only for manual verification or explicitly separated local tests.

## README And Roadmap

`README.md` must include:

- what the integration does
- installation through HACS and manual copy
- configuration flow with phone + call-code
- how selected door locks behave
- clear statement that lock state is assumed after an open command
- troubleshooting
- what happens when the SMD token expires and how Home Assistant Repairs/reauth fixes it
- privacy/security notes
- current limitations

`ROADMAP.md` must separate:

- MVP: phone + call-code auth, door discovery, selected lock entities, tests, HACS readiness
- MVP: expired-token Repairs issue and reauth flow
- Next: token refresh if the API exposes refresh tokens or silent renewal
- Later: camera streams
- Later: incoming calls and push events
- Later: guest photos or event history if feasible

## Open Implementation Questions

These questions are intentionally scoped to the reverse-engineering phase and do not block the design:

- Exact phone + call-code endpoints and payloads.
- Exact token storage and expiration model.
- Exact list-doors endpoint and stable identifiers.
- Whether the old `http://mqapp.s-m-d.ru:47393/` endpoint is still current in the latest APK.
- Whether a user-agent or app signature-derived header is required.
- Whether the API exposes a real lock command. If it does not, the MVP keeps `async_lock()` as a local assumed-state reset only.
- Whether video streams use RTSP, HLS, WebRTC, proprietary signaling, or a vendor SDK.

## Accepted Approach

The accepted approach is reverse-first:

1. Establish APK source and checksum trail.
2. Reverse-engineer auth, door discovery, open-door command, and video/call clues.
3. Write sanitized research docs.
4. Implement the Home Assistant integration only after phone + call-code auth and door discovery are understood.
5. Deliver MVP lock entities with tests and HACS-ready metadata.

This avoids building a component around manually captured tokens and keeps future iterations reproducible.
