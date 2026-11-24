# Next terminal experiment: initialization resampling

[Español](next-initialization.es.md) · [Baseline result](fixed-dynamic-pilot.en.md) · [Launcher validation](../evidence/next-initialization-validation.json)

**Execution update:** the owner has now run this experiment. [Measured results and failure analysis](resampling-result.en.md) supersede its earlier pending status. The instructions and launcher validation below describe how the experiment was prepared.

From repository PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Continue-TrueSkate.ps1
```

Use `-CheckOnly` to verify required inputs, unchanged baseline configuration, disk space, WSL and existing CUDA imports without training. The default experiment retains the baseline's 8 training cameras, cam13 reserved view, 13 instants, crops, poses, images, model settings and 200 coarse + 2000 fine steps. It reuses the existing environments and does not install packages or retrain the baseline.

The initialization changes from **1,115 to 8,920 points**. The original points remain; additional position/color samples interpolate along segments to six nearby points, with deterministic seed 24. These are synthetic initialization samples, not new measured or triangulated geometry. Interpolation can cross surface boundaries. This changes density and spatial/color distribution together, so it is an initialization variant rather than an isolated count-only ablation. It does not add board-specific seeds or foreground weighting.

Four phases report progress: GPU checks; input preparation with image identity checks; WSL copy, actual loader/projection checks, GPU training and rendering; comparison against the existing baseline. Training reports percentages, loss, training-image PSNR and point count. Fifteen-second elapsed-time messages cover quiet phases. Initial estimate: 5–15 minutes, dependent on WSL startup, transfer and GPU load.

Each execution creates a fresh `outputs/fixed-next-<UTC timestamp>/` directory. It contains `input/`, `run/`, per-phase logs and `comparison/`. The final `test-cam13-comparison.jpg` shows input / baseline / new result, and `summary.json` records metric differences. The comparator verifies that all reported target images have identical pixels before comparing metrics. A global score increase does not establish board reconstruction; inspect the images and frozen-time control. Existing source data and the baseline are preserved. Interrupted optimization is not automatically resumed from optimizer state; partial files remain available for inspection.

Launcher validation: `-CheckOnly` passed using the existing RTX 4050 environment; actual preparation retained 117 identical images; 27 helper tests passed, including planar geometry/color preservation and rejection of changed evaluation targets. The GPU loader is also checked against the resampled point count before training. The linked validation snapshot predates the owner's completed training and is not its quality result.
