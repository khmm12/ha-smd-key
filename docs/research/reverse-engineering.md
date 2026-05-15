# Reverse Engineering Notes

Date started: 2026-05-15

## Status

Reverse-engineering started from APKPure XAPK version `5.3.10` / version code `639`. Findings below are sanitized and only point to local temporary paths, checksums, commands, class names, and endpoint shapes. No APK, decompiled source, captures, phone numbers, addresses, or tokens are committed.

## Local Tool Reconnaissance

Observed on 2026-05-15:

- `uv` is available.
- Android SDK is present at `/Users/khmm12/Library/Android/sdk`.
- Android build tools are present for versions `35.0.0` and `36.1.0`.
- `adb` is available at `/opt/homebrew/bin/adb`.
- `aapt`, `aapt2`, `apksigner`, `zipalign`, `dexdump`, and `d8` are available through Android build-tools absolute paths.
- OpenJDK `25.0.2` is available at `/opt/homebrew/Cellar/openjdk/25.0.2/bin/java`, while `/usr/bin/java` may not find a runtime.
- `unzip`, `file`, `shasum`, `openssl`, `mitmproxy 12.2.3`, Docker, and `uv` are available.
- `apktool` was later installed with Homebrew.
- `jadx` was later installed with Homebrew.
- `jadx-gui` was not found in PATH.
- `apksigner` was not found in PATH.
- `bundletool` was not found in PATH.
- `apkeep` was later installed with Homebrew.
- `gplaycli` was not found in PATH.
- `frida` was not found in PATH.
- `objection` was not found in PATH.

## Required Tooling

Expected tools:

- `unzip` for inspecting XAPK/APKS containers.
- `jadx` or `jadx-gui` for Java/Kotlin decompilation.
- `apktool` for AndroidManifest/resources/smali inspection.
- `apksigner` or `keytool` for signature verification.
- `sha256sum` or `shasum -a 256` for checksum verification.
- `bundletool` if the selected artifact is an Android App Bundle or split APK set.
- `adb` for pulling official Google Play-installed split APKs from an Android device or emulator.
- `apkeep` as a fallback acquisition helper for APKPure or Google Play.

Installed tool versions used:

- `apkeep 1.0.0`
- `jadx 1.5.5`
- `apktool 3.0.2`
- `aapt2`: `Android Asset Packaging Tool (aapt) 2.20-14042983`
- Android SDK build-tools: `36.1.0`
- OpenJDK runtime used for `apksigner.jar`: `/opt/homebrew/Cellar/openjdk/25.0.2/bin/java`

## Acquisition Plan

Preferred path with a device or emulator:

```bash
adb devices
adb shell pm path com.smd.ip_smd
adb shell dumpsys package com.smd.ip_smd
adb pull /data/app/.../base.apk /private/tmp/smd-dkeys-apk/base.apk
adb pull /data/app/.../split_config.arm64_v8a.apk /private/tmp/smd-dkeys-apk/split_config.arm64_v8a.apk
```

Mirror fallback with `apkeep`, if installed later:

```bash
apkeep -l -a com.smd.ip_smd -d apk-pure
apkeep -a com.smd.ip_smd@5.3.10 -d apk-pure /private/tmp/smd-dkeys-apk
```

Google Play automation through tools such as `apkeep` or `gplaycli` may conflict with Google account terms and should use a throwaway account if used at all.

## Verification Commands

```bash
shasum -a 256 /private/tmp/smd-dkeys-apk/*.apk
/Users/khmm12/Library/Android/sdk/build-tools/36.1.0/aapt2 dump badging /private/tmp/smd-dkeys-apk/base.apk
/Users/khmm12/Library/Android/sdk/build-tools/36.1.0/aapt2 dump permissions /private/tmp/smd-dkeys-apk/base.apk
/opt/homebrew/Cellar/openjdk/25.0.2/bin/java -jar /Users/khmm12/Library/Android/sdk/build-tools/36.1.0/lib/apksigner.jar verify --verbose --print-certs /private/tmp/smd-dkeys-apk/base.apk
```

For XAPK artifacts:

```bash
unzip -l /private/tmp/smd-dkeys-apk/D-KEYS.xapk
unzip /private/tmp/smd-dkeys-apk/D-KEYS.xapk -d /private/tmp/smd-dkeys-xapk
```

For decompilation after installing missing tools:

```bash
jadx -d /private/tmp/smd-dkeys-jadx /private/tmp/smd-dkeys-xapk/base.apk
apktool d -f -o /private/tmp/smd-dkeys-apktool/base /private/tmp/smd-dkeys-xapk/base.apk
```

## Artifact Policy

Keep all APK/XAPK, unpacked APKs, decompiled sources, captures, and token-bearing notes outside git. Suggested local locations:

```text
../ha-smd-key-artifacts/
/private/tmp/ha-smd-key-artifacts/
```

Only sanitized observations, checksums, commands, and file names belong in `docs/research/`.

## Command Log

Commands run on 2026-05-15:

```bash
adb devices
```

Result: `adb` daemon started, but no Android devices were attached. Google Play pull was not available in this iteration.

```bash
brew install apkeep jadx apktool
apkeep -l -a com.smd.ip_smd -d apk-pure
apkeep -a com.smd.ip_smd@5.3.10 -d apk-pure /private/tmp/smd-dkeys-apk
unzip -l /private/tmp/smd-dkeys-apk/com.smd.ip_smd@5.3.10.xapk
unzip /private/tmp/smd-dkeys-apk/com.smd.ip_smd@5.3.10.xapk -d /private/tmp/smd-dkeys-xapk-5.3.10
shasum -a 256 /private/tmp/smd-dkeys-apk/com.smd.ip_smd@5.3.10.xapk
shasum -a 256 /private/tmp/smd-dkeys-xapk-5.3.10/*.apk
/Users/khmm12/Library/Android/sdk/build-tools/36.1.0/aapt2 dump badging /private/tmp/smd-dkeys-xapk-5.3.10/com.smd.ip_smd.apk
/opt/homebrew/Cellar/openjdk/25.0.2/bin/java -jar /Users/khmm12/Library/Android/sdk/build-tools/36.1.0/lib/apksigner.jar verify --verbose --print-certs /private/tmp/smd-dkeys-xapk-5.3.10/com.smd.ip_smd.apk
apktool d --frame-path /private/tmp/smd-apktool-framework -f -o /private/tmp/smd-dkeys-apktool-5.3.10 /private/tmp/smd-dkeys-xapk-5.3.10/com.smd.ip_smd.apk
JADX_CONFIG_DIR=/private/tmp/smd-jadx-config JADX_CACHE_DIR=/private/tmp/smd-jadx-cache JADX_TMP_DIR=/private/tmp/smd-jadx-tmp jadx -d /private/tmp/smd-dkeys-jadx-5.3.10 /private/tmp/smd-dkeys-xapk-5.3.10/com.smd.ip_smd.apk
```

Notes:

- `apktool d` needed `--frame-path /private/tmp/smd-apktool-framework` because the default framework directory is outside the writable workspace.
- `jadx` needed temporary config/cache directories under `/private/tmp`.
- `jadx` completed with 92 decompilation errors, but the relevant networking, DTO, and flow classes were readable.
- `apktool` reported some unresolved resource warnings, but manifest, resources, and smali were decoded.

Relevant decompiled locations:

- JADX source: `/private/tmp/smd-dkeys-jadx-5.3.10/sources`
- APKTool smali/resources: `/private/tmp/smd-dkeys-apktool-5.3.10`

Relevant classes and resources:

- `com.smd.core.di.NetworkModule`
- `com.smd.core.di.NetworkModuleKt`
- `com.smd.core.data.remote.ConstServersKt`
- `com.smd.core.data.remote.Utils`
- `com.smd.core.data.remote.api.WebserviceMDE`
- `com.smd.core.data.remote.api.L2Service`
- `com.smd.core.data.remote.api.WebserviceLServers`
- `com.smd.core.data.remote.source.RemoteDataSourceMDE`
- `com.smd.core.data.remote.source.RemoteDataSourceLServers`
- `com.smd.core.data.remote.entity.mdeDto.SendPinDto`
- `com.smd.core.data.remote.entity.mdeDto.KeyDto`
- `com.smd.core.data.remote.response.mdeResponse.ListKeyResponse`
- `com.smd.core.data.remote.response.lServersResponse.OpenDoorResponse`
- `com.smd.core.domain.entity.Key`
- `com.smd.key.call.Linphone`
- `com.smd.key.call.IntercomLinphone`
- `com.smd.key.call.IncomingCallActivity`

Manifest findings:

- Main activity: `com.smd.ip_smd.activity.MainActivity`
- Application: `com.smd.ip_smd.application.MainApplication`
- `android:usesCleartextTraffic="true"`
- Firebase messaging service: `com.smd.key.pushService.PushService`
- Permissions include internet, camera, record audio, phone state, foreground service camera/microphone/phone-call/data-sync, Bluetooth, location, contacts, notifications, and full-screen intent.
