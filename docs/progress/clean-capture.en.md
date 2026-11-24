# New recording: menu-hidden view recovery — 24 November 2026

[Español](clean-capture.es.md) · [Measured evidence](../evidence/clean-capture-2026-11-24.json)

The owner supplied a new unedited **567.67-second** phone recording and indicated that the replay menu was hidden for each take. Automatic processing recovered **20 passages**, retaining the original image framing. Nineteen are consistent with a fixed camera in three sampled images; view05 moves, and view18/view19 are a likely repeated viewpoint. This leaves **18 distinct fixed-view candidates**, pending synchronization and calibration.

![Midpoint previews of all 20 exported passages](../assets/clean-capture-views.jpg)

These previews occur at each passage's midpoint, not necessarily the same replay instant. IDs follow recording order and are independent of earlier datasets. They do not denote regular angular spacing. Source imagery is owner-captured True Skate gameplay; game assets belong to their respective owners.

## Extraction and verification

The existing phone-specific UI detector samples the replay interface at 10 samples/second. Menu-absent intervals of at least three seconds are screened for the red editor toolbar, so camera-placement phases are not mistaken for clean replay. Mixed intervals receive a local scan. A 0.35-second margin at both ends reduces transition contamination. Passages are then exported at 60 FPS, 1126×2436, H.264 CRF 18, without audio.

The 20 clips span **3.48–6.68 seconds** each, totaling 7,133 decoded frames and 118.88 seconds. All files were fully decoded without errors; no replay-menu pattern was detected in any exported frame. Their combined size is **17.10 MiB**. The original 986.7 MB recording's SHA-256 was verified unchanged after processing. The variable-rate source is resampled to constant 60 FPS; duplicate/drop capture-frame behavior does not create new simulation observations.

Three-frame background SIFT checks use the same displacement criteria as the previous recovery: at least 80 matches, median displacement ≤0.75 preview pixels and 90th percentile ≤2.5, at 480-pixel image width. These sampled checks are not full-sequence pose verification or calibration. Menu absence also does not guarantee absence of trick-score text or all other overlays.

## Flagged passages

![Camera-mode labels from the visible menus preceding the extracted takes](../assets/clean-capture-modes.jpg)

- **view05**, source 158.15–162.15 seconds (approximately 2 min 38 s), fails sampled fixed-camera consistency. The preceding menu visibly states **CAMERA: AUTO**. All other preceding mode labels state FIXED. This supports excluding view05 from a fixed-camera experiment; its file is retained.
- **view18 and view19** appear to share one viewpoint. Both are retained. Prefer view19 for later review because it is longer (5.78 seconds versus 3.48), subject to common-action visibility and synchronization checks.

## Local files and next gate

Clips are `data/raw/true-skate-clean-2026-11-24/view01.mp4` through `view20.mp4`; `cuts.json` contains timing, sample checks, flags and a preliminary preferred-view list. The original recording, clips and analysis traces remain local and ignored by Git. The helper, overview and compact evidence are published. No earlier clips/models were overwritten, and no training was launched.

Reproduction with the existing Windows helper environment and FFmpeg:

```powershell
.\.venv\Scripts\python.exe scripts/inspect_fixed_screenrecording.py "ScreenRecording_11-24-2026 16-58-35_1.mp4" --output outputs/fixed-clean-review
.\.venv\Scripts\python.exe scripts/recover_hidden_hud_views.py "ScreenRecording_11-24-2026 16-58-35_1.mp4" --export
```

For repeated recovery, choose a fresh `--output`; existing manifests/videos are protected against overwrite. The detector targets this 1126×2436 UI layout. The next step is to verify board visibility and align the shared action, then estimate cameras for this new dataset. **Hiding the menu supplies cut boundaries, not temporal synchronization.** Unequal passage durations and differing midpoint board states must be handled before training; earlier poses and training splits must not be reused silently.
