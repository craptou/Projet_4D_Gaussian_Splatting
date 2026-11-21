# DyNeRF bounded quality pilot — 20 November 2026

[Español](quality-pilot.es.md)

## Frozen protocol

Improve on the [twelve-step execution test](local-gpu.en.md), using the same four optimization cameras, held-out cam00, first 30 contiguous source frames and 1352 × 1014 images. No new data download or image copy. Timestamps remain `index / 300`.

Initialization selection uses training geometry only: keep points with at least three observations and mean reprojection error at most 2 pixels. This retains **3,103/3,390 points** and reduces the maximum world Z from **319.07 to 28.18**. The six points above Z=30 all had two observations; this motivates the support criterion, but does not prove those points were physically wrong. Original geometry and smoke input are preserved. The selected cloud still uses the 19 original training views; only four views enter dynamic optimization. This is not an isolated four-camera capture benchmark.

The [configuration](../../configs/experiments/dynerf-quality.py) specifies **200 coarse + 3,000 fine steps**, batch size 1. Densification is permitted at fine steps 300, 600, 900 and 1200; additional point growth is disabled. Under the current clone/split rules this bounds the point count by 3,103 × 16 = 49,648, rather than depending on the upstream 360,000-point trigger. The actual count is still checked in logs/artifacts. Only fine models 1000 and 3000 are saved; no optimizer checkpoints or training-preview image streams. The launcher requires 6 GiB free at startup and stops training if free output-disk space falls below 5 GiB. It skips installation and reuses the built CUDA extensions.

From a repository PowerShell terminal:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-LocalGPU.ps1 -Quality
```

The owner authorized this run; a visible terminal was launched for progress. Folder timestamps use UTC (`20261121-002150Z`); the local date is 20 November in Bogotá. The run is `outputs/dynerf-quality-20261121-002150Z/`. Do not launch a second copy while it is active. Check the actual report/logs for completion; this protocol alone is not a result.

## Evaluation

Render all 30 cam00 frames from models at fine steps 1000 and 3000. Compare each against its original target and the smoke output, checking identical target pixels and dimensions across runs. Save a visual progression at frames 0, 14 and 29, and per-frame/mean PSNR and SSIM on full RGB PNG images. PSNR uses normalized RGB MSE; SSIM uses scikit-image's Gaussian window (sigma 1.5, channel axis 2, population covariance, range 1). No masks or linear color conversion. LPIPS is not measured; no network weights are downloaded.

cam00 is excluded from optimization but already inspected and monitored, so it is a **validation camera**, not a fresh independent final test. Longer optimization, initialization selection and densification change together: improvement cannot be attributed to any one change. A controlled ablation would require separate runs. This remains a reduced-scene compatibility experiment, not reproduction of the paper's benchmark.

Scripts/checks: `prepare_quality_reference.py` preserves identical images/calibration via hard links; actual upstream loader checks the split/shape/time; the low-disk guard was verified with a subprocess that stops on an intentionally impossible reserve. Syntax/check-only checks passed before launch.
