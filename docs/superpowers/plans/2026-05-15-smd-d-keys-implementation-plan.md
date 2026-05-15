# SMD D-KEYS Implementation Plan

Date: 2026-05-15

Design spec: `docs/superpowers/specs/2026-05-15-smd-d-keys-design.md`

## Phase 0: Repository Baseline

- Create HACS-ready repository skeleton.
- Add `pyproject.toml` managed with `uv`.
- Configure `ruff`, `pytest`, and Home Assistant custom component tests.
- Add `.gitignore` entries for reverse-engineering artifacts, APK/XAPK files, virtualenvs, caches, and secrets.
- Keep Conventional Commits.

## Phase 1: Research Trail

- Create `docs/research/`.
- Record PoC findings from `home-pi`.
- Record APK source candidates for `com.smd.ip_smd`.
- Download the selected APK/XAPK outside git.
- Record exact source URL, date, version, version code, size, SHA256, and signing certificate fingerprint.
- Record reverse-engineering tool versions and commands.

## Phase 2: Reverse Engineering

- Inspect manifest, resources, strings, and decompiled classes.
- Identify phone + call-code request flow.
- Identify call-code exchange/token response.
- Identify token expiration/refresh/reauth behavior.
- Identify list houses/doors API.
- Confirm or update the PoC `openDoor` endpoint and request schema.
- Collect camera/video/call findings for roadmap docs only.
- Update `docs/research/api.md` and `docs/research/video-and-calls.md`.

## Phase 3: Home Assistant MVP

- Implement `custom_components/smd_d_keys`.
- Add `manifest.json`, `strings.json`, translations, constants, typed runtime data, API client, config flow, options flow, coordinator/runtime helpers, diagnostics, and `lock` platform.
- Config flow must use phone + call-code only, then door discovery and door selection.
- Options flow must support selected doors and `relock_delay`.
- Auth failures must raise `ConfigEntryAuthFailed` and drive HA Repairs/reauth.
- Locks must expose assumed recent-open state and return to locked after `relock_delay`.

## Phase 4: Tests

- Add mocked API fixtures.
- Cover config flow, call-code errors, duplicate account, options flow, setup/unload, reauth, diagnostics redaction, and lock behavior.
- Use time control for relock-delay tests.
- Keep live credentials out of tests and git.

## Phase 5: Packaging And Docs

- Add `README.md`, `ROADMAP.md`, `hacs.json`, and validation workflow.
- Document installation, config, lock semantics, Repairs/reauth, limitations, and privacy.
- Run lint/tests where the local environment allows.

## Current Constraints

- `uv` is available locally.
- `apktool`, `jadx`, `jadx-gui`, `apksigner`, and `bundletool` were not found in PATH during initial reconnaissance.
- Network access and tool installation may need explicit approval.
- The MVP is blocked on confirmed phone + call-code auth and door discovery details.
