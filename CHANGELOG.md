# Changelog

## 0.1.2 - 2026-11-26

- Build the SMD TLS context in the executor instead of the event loop.

## 0.1.1 - 2026-11-26

- Fix setup failing because the SMD servers currently serve an incomplete TLS
  chain. The integration trusts the missing GlobalSign intermediate for SMD
  requests only; certificate and hostname verification stay enabled.

## 0.1.0 - 2026-05-16

- First release: phone and call-code authentication, door lock entities with an
  assumed state, live RTSP camera entities, and reauthentication when SMD
  rejects the token.
