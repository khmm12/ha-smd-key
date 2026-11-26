# ROADMAP

## MVP

- Phone + OTP config flow.
- Token storage through Home Assistant config entries.
- Door discovery through `getKey`.
- User-selected `lock` entities.
- Assumed lock state with configurable relock delay.
- User-selected live `camera` entities for doors that advertise `videoTranslate`.
- RTSP stream URL acquisition through the Android app's `getNewVideo` and `getVideoBroadcastByProtocol` flow.
- Reauth/Repairs path when the token is rejected.
- Notification polling through `getUnread`, with an `event` entity for calls and other pushes.
- Last guest photo through the signed photo URL, exposed as an `image` entity.
- RTSP source refresh when an existing stream fails.
- Tests and sanitized research documentation.

## Next

- Live validation of notification polling with a real doorbell ring and a guest photo.
- More accounts and panel models.
- Better classification of SMD auth, rate-limit, and account-state errors.
- AWA key research and optional support.
- Camera archive playback and record-link retrieval.
- WebRTC-specific handling if HA/go2rtc RTSP is not enough for some panels.
- Incoming call signaling through FCM/RuStore push instead of polling.
- Guest photo retention if SMD adds a stable image endpoint.
- HACS validation hardening and release automation.
