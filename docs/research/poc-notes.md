# SMD D-KEYS PoC Notes

Date started: 2026-05-15

## Location

Existing proof of concept on `home-pi`:

```text
~/services/smarthome/data/homeassistant/custom_components/smd_d_key/
```

## Initial Findings

Files observed:

- `__init__.py`
- `config_flow.py`
- `const.py`
- `lock.py`
- `manifest.json`
- `smd_door_client.py`
- `__pycache__/` bytecode files ignored

No hard-coded user tokens or door IDs were observed in the source files inspected. The PoC is a manually configured single-door integration. It asks for:

- `title`
- `session_token`
- `door_id`

It stores:

- `session_token`
- `door_id`

## Manifest Fields

Observed manifest fields:

- `domain`: `smd_d_key`
- `name`: `SMD D-Key`
- `config_flow`: `true`
- `requirements`: empty list
- `dependencies`: empty list
- `codeowners`: empty list
- `version`: `1.0.0`

Missing from the PoC manifest:

- `iot_class`
- `integration_type`
- documentation URL
- issue tracker URL
- code owner

## Config Flow Behavior

The config flow:

- creates the entry immediately after form submission
- does not validate token, door ID, endpoint reachability, or credentials
- does not prevent duplicate entries
- does not set a config entry unique ID
- uses `CONN_CLASS_LOCAL_PUSH`, although observed behavior is a cloud HTTP POST and not local push

## Setup Behavior

- `PLATFORMS = ["lock"]`
- `async_setup` returns `True`
- `async_setup_entry` forwards setup to the lock platform with a created task and returns `True`
- `async_unload_entry` unloads the lock platform

Modernization notes:

- platform forwarding should be awaited rather than fire-and-forget
- runtime objects should use `entry.runtime_data`
- shared API/coordinator lifecycle is missing

## Open Door Clue

The PoC sends a form POST:

```text
POST http://mqapp.s-m-d.ru:47393/
action=openDoor
token=<session_token>
topic=<door_id>
text=cmd1
```

The response is parsed as JSON without content-type validation. The PoC treats `error == "false"` as success and raises an exception with the server message otherwise.

Live comparison on 2026-05-16:

- The working PoC config on `home-pi` used a `door_id` shaped like `smd/...`.
- The new app auth flow returned `codeMP`, but not the MQTT open topic in `getKey`.
- Sending `topic=<codeMP>` to the legacy PoC endpoint returned `accsess error`.
- Fetching `getDataOption` with `option=mqtt` and the key's `codeKey` returned the real `topicCommand` and `openCommand`.
- Sending that `topicCommand` and `openCommand` to the Android CMDC `/openDoor` endpoint returned `DATA=OK`.

Conclusion: do not derive the open topic from `codeMP`. For current API data, use `getKey.mqtt`/`getKey.text` when present, otherwise call `getDataOption(option=mqtt, codeKey=<codeKey>)`.

## Client Code Behavior

`SmdDoorClient`:

- uses `aiohttp`
- accepts `token`, `door_id`, and optional `websession`
- creates its own `aiohttp.ClientSession` if no session is passed
- `open()` calls `call_action("openDoor")`
- `call_action()` sends `aiohttp.FormData`
- the lock platform passes Home Assistant's shared aiohttp session through `async_get_clientsession(hass)`

Limitations:

- no HTTP status handling
- no timeout
- no retry or backoff
- no explicit network error mapping
- no invalid JSON handling
- no guard for missing `error` or `message`
- assumes the API returns string `"false"` instead of boolean `false`
- self-created aiohttp sessions are not closed when used outside the HA shared session path

## Lock Behavior

The PoC exposes one `LockEntity`. The state is assumed:

- initial state is locked
- `async_unlock()` calls the open-door endpoint
- successful unlock sets local state to unlocked
- a timer returns local state to locked after 5 seconds
- `is_locked` returns the local state
- `async_lock()` is empty and does not perform a real API lock command

This is useful UI behavior but not a real door sensor or verified magnetic lock state.

Other entity notes:

- `unique_id` is derived from configured `door_id`
- no explicit entity name property
- no `device_info`
- no availability handling
- no polling/coordinator refresh
- `should_poll` is implemented like a method rather than a property

## Differences In New Integration

- Domain becomes `smd_d_keys`.
- One config entry represents one SMD account.
- Manual token entry is forbidden.
- Config flow must use phone + call-code auth.
- Door discovery must come from the API.
- The user can choose which account doors become entities.
- Expired or revoked auth must surface through Home Assistant Repairs/reauth.
