# SMD D-KEYS RTSP Camera Design

Date: 2026-05-16

## Goal

Add live intercom camera support to the Home Assistant `smd_d_keys` custom integration.

This iteration is intentionally limited to live camera entities. Video archive, incoming calls, call events, snapshots from calls, and WebRTC playback remain out of scope.

## Reverse-Engineered Flow

The Android app does not receive a permanent stream URL from `getKey`. It discovers camera metadata first, then requests a temporary live stream URL from the selected L-server.

MDE camera metadata:

```text
POST https://mde.s-m-d.ru:38257/DKeys_app_3/MAIN.php/
action=getNewVideo
codeKey=<door codeKey>
...common app params...
```

Expected `DATA` shape is a `BroadcastDto` with fields such as:

- `codeKey` / domain `code`
- `Nickname`
- `Address`
- `codeMP`
- `protocol`
- `srv`
- `UID`
- `Online`
- `Record`
- `recordStoragePeriod`

Live stream URL:

```text
POST <broadcast.srv>/app/getVideoBroadcastByProtocol
Content-Type: application/json
```

Payload includes common app params plus:

- `action=getVideoBroadcastByProtocol`
- `codeMP=<broadcast codeMP>`
- `protocol=RTSP`

Expected `DATA` shape is a link DTO:

- `url`
- `login`
- `password`
- `protocol`

For RTSP, Home Assistant should expose:

```text
rtsp://<login>:<password>@<url>
```

The Android app also supports WebRTC, but RTSP is the MVP path because Home Assistant and go2rtc handle RTSP well.

## Home Assistant Behavior

Add `camera` to the integration platforms.

Camera entities are created for selected doors when:

- the door advertises `videoTranslate` in `options_exist` or `options`;
- the door has a `codeKey`;
- `getNewVideo(codeKey)` returns usable broadcast metadata.

The camera entity should:

- use the same device as the corresponding lock entity;
- have a stable unique ID derived from the door ID plus camera suffix;
- implement `Camera.stream_source()` and return a fresh RTSP URL;
- avoid storing temporary stream credentials in config entry data, options, diagnostics, or entity attributes;
- surface authentication failures through the existing reauth/Repairs behavior.

If stream URL retrieval fails because of network or SMD API errors, the entity may remain present, but `stream_source()` should raise an appropriate Home Assistant error and log only redacted details.

## Data Model

Extend runtime models with a camera/broadcast model that contains only data needed to request a stream:

- hashed/stable ID
- title
- address, only for entity naming when already available
- `code_key`
- `code_mp`
- `srv`
- `protocol`
- `online`

Do not include `login`, `password`, or full RTSP URL in stored runtime coordinator data longer than the stream request needs.

## API Client

Add methods to `SmdDKeysClient`:

- `async_get_camera_for_door(door: SmdDoor) -> SmdCamera | None`
- `async_get_camera_stream_source(camera: SmdCamera, protocol: str = "RTSP") -> str`

Server discovery already records L-server domains. The `srv` field from `BroadcastDto` should select the correct discovered server when possible. If `srv` is already a URL, use it directly. If no matching server is available, raise a malformed response error rather than guessing.

## Options And Selection

MVP follows the existing selected-door list. If a door is selected for lock exposure and it has camera metadata, the camera is exposed too.

A separate "choose lock vs camera per door" UI can be added later. The current options flow remains focused on selected doors and relock delay.

## Tests

Add focused tests:

- API: `getNewVideo` parses broadcast metadata.
- API: `getVideoBroadcastByProtocol` builds an RTSP URL without logging credentials.
- Camera platform: selected video-capable door creates a camera entity.
- Camera platform: `stream_source()` returns the expected RTSP URL.
- Negative: door without `videoTranslate` does not create a camera entity.

Existing lock and config-flow tests must keep passing.

## Documentation

Update:

- `docs/research/video-and-calls.md` with the validated camera flow.
- `README.md` with live camera support and the RTSP/go2rtc expectation.
- `ROADMAP.md` to move live camera from future work into MVP/current support, while keeping archive and incoming calls as future work.

## Out Of Scope

- WebRTC entity support.
- Video archive browsing and recordings.
- Incoming call signaling.
- SIP/Linphone integration.
- Push notification registration.
- Manual stream URL configuration.
