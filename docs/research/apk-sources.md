# APK Sources

Date started: 2026-05-15

## Package

- Package name: `com.smd.ip_smd`
- App name: `D-KEYS`
- Developer/publisher observed: `Платформа D-Keys`
- Home Assistant integration domain: `smd_d_keys`

## Public Sources Observed

### Google Play

- URL: `https://play.google.com/store/apps/details?id=com.smd.ip_smd`
- Observed on: 2026-05-15
- App name: `D-KEYS`
- Developer: `PLATFORMA D-KEIS, OOO` / `Платформа D-Keys`
- Category: House & Home
- Downloads: `100K+`
- Updated on: `Apr 27, 2026`
- Notes: official store listing; does not directly expose APK files.

### APKPure

- URL: `https://apkpure.com/ru/d-keys/com.smd.ip_smd/download/`
- Observed on: 2026-05-15
- Freshest listed version from `apkeep` APKPure index: `5.3.10`
- Freshest listed package type: `XAPK`
- Downloaded artifact: `/private/tmp/smd-dkeys-apk/com.smd.ip_smd@5.3.10.xapk`
- Downloaded with: `apkeep -a com.smd.ip_smd@5.3.10 -d apk-pure /private/tmp/smd-dkeys-apk`
- Local XAPK size: `56.1M`
- Local XAPK SHA256: `dc3f0f253c8cde79e1beefce94d539885a9c8843df6284c085263d31fc1a079e`
- XAPK manifest package: `com.smd.ip_smd`
- XAPK manifest app name: `D-KEYS`
- XAPK manifest version name: `5.3.10`
- XAPK manifest version code: `639`
- XAPK manifest min SDK: `24`
- XAPK manifest target SDK: `35`
- XAPK splits inspected:
  - `com.smd.ip_smd.apk`
  - `config.armeabi_v7a.apk`
  - `config.mdpi.apk`
- Brand asset reused by the Home Assistant integration:
  - XAPK top-level `icon.png`
  - Dimensions: `512x512`
  - Destination: `custom_components/smd_d_keys/brand/icon.png`
- Notes: APKPure is a mirror source. The artifact was kept outside git and verified locally before reverse-engineering.

Local split checksums from `/private/tmp/smd-dkeys-xapk-5.3.10`:

| File | SHA256 |
| --- | --- |
| `com.smd.ip_smd.apk` | `af3f4bd12ce473697d530c8456b2269dc3a66f939296991b24f78e2153c0f14f` |
| `config.armeabi_v7a.apk` | `5250c98384ca1deda39cbc1ce2608dbb015072e2fe29c1cc71d4a491f62f0275` |
| `config.mdpi.apk` | `5a462a4684724b0ec53e68a23641d6bf697433a7ad7a3723df83813a2be5f624` |

Signature verification for `com.smd.ip_smd.apk`:

- Verified schemes: APK Signature Scheme v2 and v3.
- SourceStamp: verified.
- Signer certificate SHA-256: `c60c480cda0dad6fdc7e9a1dafb42daedc6922af35ff245447d4d3257a25efff`
- Signer certificate SHA-1: `17034bbb9b5f0bca6972acd3b180d41ae7cdfd2c`
- Signer certificate MD5: `132857b9aa3054c3a6fef1fada06aeda`
- Certificate DN: `CN=Android, OU=Android, O=Google Inc., L=Mountain View, ST=California, C=US`

The SHA-1 certificate fingerprint matches the historical APKPure observation below, which is useful continuity evidence for the mirror artifact.

Historical APKPure observation from localized download page:

- Listed latest version: `5.2.6`
- Listed version code: `616`
- Listed package type: `XAPK APKs`
- Listed update date: `01/07/2025`
- Listed Android requirement: Android 7.0+ / API 24+
- Listed signature fingerprint: `17034bbb9b5f0bca6972acd3b180d41ae7cdfd2c`
- Listed arm64-v8a variant size: `73.0 MB`
- Listed arm64-v8a variant SHA1: `311b705edf669d9727cd404ae3be1e67d383b567`
- Listed arm64-v8a variant SHA256: `87386e2539ce7c27ece67fe922da94fdf9dc6361422bc170b1cc9878f2dd4da6`
- Listed arm64-v8a splits: `com.smd.ip_smd.apk`, `config.arm64_v8a`, `config.xxxhdpi`
- Listed armeabi-v7a variant size: `65.7 MB`
- Listed armeabi-v7a variant SHA1: `69b5dd50bf1a0f46e364b3e1db1133c0f2aaa7c4`
- Listed armeabi-v7a splits: `com.smd.ip_smd.apk`, `config.armeabi_v7a`, `config.mdpi`

### APKCombo

- URL: `https://apkcombo.com/d-keys/com.smd.ip_smd`
- Observed on: 2026-05-15
- Listed latest version on page: `5.2.1`
- Listed version code: `607`
- Listed update date: `Apr 5, 2025`
- Listed package size: `65 MB`
- Notes: useful fallback and old-version index, but stale compared with Google Play and APKPure observations.

## Download Status

No APK/XAPK file has been committed to this repository. Binary artifacts and decompiled output are kept under `/private/tmp`.

## Candidate Selection

Preferred acquisition path:

1. Install `D-KEYS` from Google Play on a real Android device or emulator.
2. Pull the installed split APKs with `adb`.
3. Use mirror downloads only as fallback or comparison material.

Mirror fallback:

- Use APKPure through `apkeep` as the current fallback path when no Google Play-installed device is attached.
- Re-check Google Play and APKPure immediately before downloading.
- Verify the signing certificate locally and compare it with any Google Play pull before trusting a mirror artifact.
