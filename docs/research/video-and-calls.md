# Video And Calls Notes

Date started: 2026-05-15

## Status

Live RTSP camera entities are part of the MVP as of 2026-05-16. Incoming calls, push signaling, guest photos, archives, and WebRTC-specific handling remain future work.

Implemented MVP flow:

1. Fetch the account camera/broadcast list from MDE `getVideo`.
2. Match broadcasts back to selected doors by `codeKey` when possible.
3. Resolve the broadcast `srv` through `getServers` entries such as `L3` / `L6`.
4. Fetch an expiring RTSP credential bundle from `/app/getVideoBroadcastByProtocol`.
5. Return `rtsp://<login>:<password>@<url>` from Home Assistant `Camera.stream_source()`.

The integration requests `protocol=RTSP` and leaves restreaming to Home Assistant/go2rtc.

## APK Findings

Video/call work is split between MDE bootstrap calls and LServers dynamic JSON endpoints.

Confirmed constants:

- `/app/getVideoBroadcastByProtocol`
- `/app/getVideoArchiveRecord`
- `/app/getRecordStoragePeriod`
- `/app/getLinkVideoArchiveOnline`
- `/app/fixedVideoTranslate`
- `/app/fixedCall`
- `app/call`

`getVideoBroadcast` payload includes:

- `action=getVideoBroadcastByProtocol`
- `codeMP`
- `protocol`

`getVideo` MDE payload:

- `action=getVideo`

`getNewVideo` MDE payload:

- `action=getNewVideo`
- `codeKey`

`BroadcastDto` JSON fields confirmed from `BroadcastDto.java`:

- `codeKey`
- `Nickname`
- `Address`
- `codeMP`
- `protocol`
- `srv`
- `UID`
- `Online`

Live validation on 2026-05-16 showed the important distinction between `getVideo` and `getNewVideo`. A door may advertise `videoTranslate`, but `getNewVideo(codeKey)` can still return warning `Warning #3.28.2 У вас нет видеокамер для просмотра.` with `DATA` as a one-item list whose broadcast fields are blank. The actual camera visible in the app was returned by account-level `getVideo`.

Live validation on 2026-05-16 also showed `srv=L3` stream credentials timing out through the uppercase `L3` server URL from `getServers` and succeeding through the later lowercase `l3` URL. The integration therefore normalizes aliases and lets the later entry win for camera server lookup.

Observed protocols:

- `RTSP`
- `WebRTC`

Stream response DTO fields:

- `url`
- `protocol`
- `login`
- `password`

Archive response DTO fields:

- `link`
- `login`
- `password`
- `task`
- `result`

Incoming calls use Linphone/SIP classes:

- `com.smd.key.call.Linphone`
- `com.smd.key.call.IntercomLinphone`
- `com.smd.key.call.IncomingCallActivity`

Observed URL construction:

- SIP addresses use `sip:` URIs.
- RTSP call video is built as `rtsp://<login>:<password>@<url>`.
- WebRTC call path loads an HTTPS URL in a WebView.

Push handling:

- `com.smd.key.pushService.PushService` handles `com.google.firebase.MESSAGING_EVENT`.
- RuStore push receiver/provider classes are also present.
- VoIP push registration uses MDE action `addTokenForVoipPush` with `pushService` and `tokenPush`.
- Push action constants include `receiveCall`, `Photo`, `photoCall`, `VideoArchive`, `Text`, `TextLink`, `pdf`, `AWACall`, and `pushGetUpdate`.

LServers call endpoints:

- `/app/fixedCall` fields include `callID`, `OpenDoor`, `ViewVideo`, `isAudio`, `timeCall`, `AcceptCall`, and `fsGroup`.
- `app/call` fields include `codeMP`, `calls`, and `numberRoom`.

## Public Store Clues

The Google Play listing observed on 2026-05-15 says the app includes a guest photo feature for video calls: during an intercom video call, a push notification can include a guest photo, and after the call the user can view/download it in the app.

APKPure's observed Android permissions include:

- `android.permission.BLUETOOTH_ADVERTISE`
- `android.permission.WAKE_LOCK`
- `android.permission.DISABLE_KEYGUARD`
- `android.permission.POST_NOTIFICATIONS`
- `android.permission.ACCESS_NOTIFICATION_POLICY`
- `android.permission.READ_PHONE_STATE`
- `android.permission.RECEIVE_BOOT_COMPLETED`
- `android.permission.USE_FULL_SCREEN_INTENT`
- `android.permission.SYSTEM_ALERT_WINDOW`
- `android.permission.ACCESS_FINE_LOCATION`
- `android.permission.ACCESS_COARSE_LOCATION`
- `android.permission.READ_CONTACTS`
- `com.google.android.c2dm.permission.RECEIVE`
- `android.permission.CHANGE_WIFI_MULTICAST_STATE`
- `android.permission.FOREGROUND_SERVICE_CAMERA`
- `android.permission.FOREGROUND_SERVICE_MICROPHONE`
- `android.permission.FOREGROUND_SERVICE_PHONE_CALL`
- `android.permission.FOREGROUND_SERVICE_DATA_SYNC`

These are clues for later reverse-engineering, not MVP requirements.

## Required Future Findings

- Live validation across more panels and accounts.
- Incoming call signaling flow.
- Push notification provider and payload shape.
- Archive playback and record-link flow.
- Guest photo endpoint and access control.
- Whether Home Assistant should model future functionality as `camera`, events, notifications, or services.
