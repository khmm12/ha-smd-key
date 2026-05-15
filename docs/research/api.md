# API Notes

Date started: 2026-05-15

## Status

Phone + call-code authentication, token response shape, door discovery, and open-door behavior are confirmed from the Android APK `com.smd.ip_smd` version `5.3.10` / version code `639`.

Live validation with user-provided credentials on 2026-05-16 confirmed initial setup and door opening from the custom integration. Camera stream acquisition is implemented from APK findings and still needs live panel validation.

Manual token entry is explicitly outside the MVP.

## Network Roots

Confirmed in `NetworkModuleKt.java` and `NetworkModule.java`:

- MDE base URL: `https://mde.s-m-d.ru:38257/DKeys_app_3/MAIN.php/`
- L2 / CMDC base URL: `https://cmdc.s-m-d.ru:8626/`

The app creates:

- `WebserviceMDE` for form-encoded `POST ./` requests.
- `L2Service` for dynamic `@Url` JSON body requests.
- `WebserviceLServers` for camera/call dynamic `@Url` JSON body requests.

The app's OkHttp setup is permissive: it accepts compatible TLS and cleartext connection specs and has a hostname verifier that returns true. The Home Assistant integration should use normal TLS verification unless real validation shows the server requires otherwise.

## Common Parameters

`Utils.buildParamsRequest` adds these fields to most MDE and L2 requests:

| Field | Observed source |
| --- | --- |
| `os` | `UserManager.getOsType()`, app sets `Android` |
| `lang` | `UserManager.getLanguageApp()` |
| `version` | Android app `versionName`, inspected artifact is `5.3.10` |
| `token` | saved `user_token`, empty before login |
| `mobile` | normalized phone, explicit during auth or saved after login |
| `versionOS` | Android `Build.VERSION.RELEASE` |

The custom integration mirrors this envelope and defaults to:

- `os=Android`
- `lang=ru`
- `version=5.3.10`
- `versionOS=15`

These defaults should be adjusted only if live validation shows SMD rejects non-app environments.

## Phone And Call-Code Auth

Both auth calls use:

```text
POST https://mde.s-m-d.ru:38257/DKeys_app_3/MAIN.php/
Content-Type: application/x-www-form-urlencoded
```

Call request:

```text
action=regPhone
mobile=<normalized phone>
os=Android
lang=<app language>
version=<app version>
token=
versionOS=<android version>
```

Call-code verification:

```text
action=sendPin
mobile=<normalized phone>
otp=<last 6 digits of caller number>
os=Android
lang=<app language>
version=<app version>
token=
versionOS=<android version>
```

The Android UI clarifies that this is a phone-call based challenge, not a regular SMS OTP:

- `your_phone_number`: the app says it will place a call from a unique number.
- `sms_send_massage`: the user should enter the last 6 digits of the number that called, hang up, and confirm.
- `try_reauthorisation`: requests another authentication call.
- `retry_auth`: shows when another call can be requested.

`PassCallScreeningService` broadcasts `com.smd.PasswordIncomingCall` with the caller `phoneNumber`, so the Android app can try to read the incoming caller number automatically. The Home Assistant integration cannot read the user's phone calls, so its config flow asks the user to manually enter the last 6 digits. Those digits are still sent to the API as field `otp`.

Response model for `sendPin`:

```json
{
  "error": false,
  "message": "...",
  "warning": "...",
  "critical": "",
  "DATA": {
    "PhoneNumber": "...",
    "Token": "..."
  }
}
```

On success the Android app calls `UserManager.login(phone, token)` and stores:

- token under SharedPreferences key `user_token`
- phone under key `phone`
- login flag under key `is_user_logged_in`

No refresh token flow, `Authorization` header, cookie session, or bearer auth was found. Subsequent calls pass the token in the `token` form/body field.

## Server Discovery

The app calls MDE `getServers` after login:

```text
action=getServers
token=<session token>
mobile=<normalized phone>
...
```

Response `DATA` contains items shaped as:

```json
{
  "server": "CMDC",
  "domen": "https://cmdc.s-m-d.ru:8626"
}
```

`UserManager.setServers` stores the `CMDC` server as the command server used for door opening.

Observed `getServers` responses can include both uppercase and lowercase names for the same logical server, for example `L3` and `l3`. Live validation on 2026-05-16 showed `srv=L3` broadcast streams time out through the uppercase `L3` URL (`http://arsav...`) but work through the later lowercase `l3` URL (`https://vrs...`). The integration normalizes server names case-insensitively and lets the later alias win.

## Door Discovery

The regular key list uses MDE `getKey`:

```text
action=getKey
token=<session token>
mobile=<normalized phone>
...
```

The AWA key list uses `getKeysAWA`, but AWA-specific behavior is not in MVP.

`ListKeyResponse`:

```json
{
  "error": false,
  "message": null,
  "warning": null,
  "critical": "",
  "DATA": [
    {
      "Nickname": "...",
      "Address": "...",
      "mqtt": "...",
      "text": "...",
      "uid": "...",
      "codeMP": "...",
      "roomNumber": "..."
    }
  ]
}
```

Relevant `KeyDto` fields:

- `Nickname`: display title.
- `Address`: display/address text, sensitive.
- `mqtt`: MQTT topic used as `topic` for opening.
- `text`: command string used as `command` for opening.
- `uid`: server-side key UID, present but not used by `openDoor`; L2 derives `uid` from `mqtt`.
- `codeMP`: panel/intercom code, useful for future video/call APIs.
- `roomNumber`: apartment/room number, sensitive.

Live validation showed that `getKey` may omit `mqtt`, `text`, and `uid` even when `options_exist` contains `mqtt`. Android handles this by treating those fields as nullable and later fetching option data. It is not a header-dependent alternate response.

For keys that advertise the `mqtt` option but do not include `mqtt`/`text`, fetch:

```text
POST <MDE>
action=getDataOption
option=mqtt
codeKey=<codeKey from getKey>
...common app params...
```

Observed response on 2026-05-16:

```json
{
  "error": false,
  "critical": "10",
  "DATA": {
    "mqtt": {
      "topicCommand": "smddev2/...",
      "openCommand": "cmd1"
    }
  }
}
```

Use `topicCommand` as `Key.mqtt` and `openCommand` as `Key.info` for opening. `codeMP` is not an open-door topic; sending `topic=<codeMP>` to the old L2 PoC endpoint returned `{"error":"true","message":"accsess error"}`. Sending the `topicCommand`/`openCommand` pair to `<CMDC>/openDoor` returned `{"error":false,"DATA":"OK"}` in local Home Assistant testing.

`MqttDto` contains `openCommand` and `topicCommand`. Static search did not find the old PoC literals `cmd1`, `cmd2`, or `cmd3` in the direct open path; the confirmed `openDoor(Key)` path uses `Key.info`, which can come either from `KeyDto.text` or from `getDataOption(...).DATA.mqtt.openCommand`.

The Home Assistant integration stores only hashed door IDs in options. Raw topics, commands, and addresses are fetched at runtime from SMD and must be redacted from diagnostics.

## Open Door

Confirmed from `RemoteDataSourceLServers.smali`, because JADX could not fully decompile this method.

The Android app uses:

```text
POST <CMDC>/openDoor
Content-Type: application/json
```

Payload:

```json
{
  "action": "openDoor",
  "topic": "<key.mqtt>",
  "command": "<key.info / KeyDto text>",
  "uid": "<substring after first slash in key.mqtt>",
  "os": "Android",
  "lang": "<app language>",
  "version": "<app version>",
  "token": "<session token>",
  "mobile": "<normalized phone>",
  "versionOS": "<android version>"
}
```

Response model:

```json
{
  "error": false,
  "message": null,
  "warning": null,
  "DATA": "..."
}
```

The app treats `error=true` as a failure and raises the server `message` if present.

## Known From PoC

The old PoC used a manually captured token and sent:

```text
POST http://mqapp.s-m-d.ru:47393/
action=openDoor
token=<session_token>
topic=<door_id>
text=cmd1
```

Observed PoC success condition:

```text
response_json["error"] == "false"
```

This endpoint and response shape are a starting clue only. They must be confirmed against the current APK before implementation.

Current APK behavior differs from PoC:

- Endpoint changed from `http://mqapp.s-m-d.ru:47393/` to `<CMDC>/openDoor`.
- Transport changed from form fields to JSON body for door opening.
- Field `text=cmd1` changed to `command=<Key.info>`, where `Key.info` is mapped from `KeyDto.text`.
- `topic` is still conceptually the door topic. It can come from `getKey.mqtt`, or from `getDataOption(option=mqtt).DATA.mqtt.topicCommand` when `getKey` only advertises `options_exist=["mqtt"]`.

## Required Findings

- Token expiration and refresh behavior: no refresh flow found; invalid token must trigger reauth.
- Account identifier used for config entry uniqueness: no explicit account ID found; normalized phone from `DATA.PhoneNumber` is the MVP fallback.
- Auth failure response that should map to Home Assistant `ConfigEntryAuthFailed`: exact server message still needs live validation.
- Rate limit response, if present: not found in static reverse-engineering.
- Timeout expectations: app uses a 15000 ms read timeout.
