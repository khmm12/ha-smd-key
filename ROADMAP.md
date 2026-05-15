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
- Tests and sanitized research documentation.

## Next

- Live validation with test credentials.
- Better classification of SMD auth, rate-limit, and account-state errors.
- AWA key research and optional support.
- Camera stream hardening after more live accounts are tested.
- Camera snapshots, if SMD exposes a stable image endpoint.
- Camera archive playback and record-link retrieval.
- WebRTC-specific handling if HA/go2rtc RTSP is not enough for some panels.
- Incoming call and push-event research.
- Guest photo retrieval research.
- HACS validation hardening and release automation.
