# Changelog

## 0.2.5 - 2026-11-26

- Mark the account-level notification device as a service and name it
  "Уведомления <account>" instead of duplicating the intercom device name.

## 0.2.4 - 2026-11-26

- Poll unread notifications every 5 seconds instead of 30, so a doorbell call
  is reported while it is still ringing. The empty unread response is small;
  the heavier history reconciliation stays on a 15-minute timer.

## 0.2.3 - 2026-11-26

- Treat a stored zero notification cursor as uninitialized, so upgrades from
  0.2.1 record the history baseline instead of replaying old notifications.

## 0.2.2 - 2026-11-26

- Reconcile the notification history every 15 minutes, so a push that the phone
  app acknowledges before the next poll is still seen by Home Assistant. The
  first sync records the current history without replaying old events.

## 0.2.1 - 2026-11-26

- Fix notification cursor persistence with the Home Assistant storage API.
- Initialize the image entity with the Home Assistant image base class so the
  guest photo entity can be added.

## 0.2.0 - 2026-11-26

- Add a notification event entity for incoming calls, guest photos, and other
  SMD pushes. The integration polls unread notifications; no Firebase
  registration is needed.
- Add a last guest photo image entity that downloads the signed HTTPS file
  pushed with a photo notification.
- Refresh the stored RTSP source when an existing camera stream has failed, so
  expired stream credentials can recover without reloading the entry.
- Run ruff and pytest in GitHub Actions and ship a 256x256 brand icon.

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
