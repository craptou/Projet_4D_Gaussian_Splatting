# Longer-training control: launcher ready

[Español](duration-control.es.md) · [Validation evidence](../evidence/duration-launcher-validation.json) · [Previous initialization experiment](resampling-result.en.md)

The owner proposed testing whether the earlier 2,000-step budget was insufficient. **The longer-training experiment is prepared but has not been executed by the assistant.** Earlier initialization results do not answer the duration question.

From repository PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Train-TrueSkate-Long.ps1
```

`-CheckOnly` verifies original input/configuration hashes, required images, free space and existing WSL/CUDA imports without training. The launcher uses the original **1,115-point initialization**, not the resampled variant, with the same 8 training cameras, reserved cam13, 104 training images and 13 reserved images over 0.4 seconds. It starts a fresh training trajectory with the upstream seed and does not overwrite prior models.

The duration configuration inherits the first pilot and overrides only `OptimizationParams.iterations=10000`. The effective MMCV configuration is checked before training. It retains 200 coarse steps, the learning-rate schedules, losses, network, crop, poses, images and densification schedule, whose end remains at step 1,300. Additional steps optimize the existing representation; this does not extend the point-growth phase. The original SH schedule also remains active: degree 2 at fine step 2,000 and maximum degree 3 at steps 5,000/10,000.

One training run saves and evaluates checkpoints at **2,000, 5,000 and 10,000 fine steps**. Terminal output streams progress, training loss/PSNR and point count, with elapsed-time messages every 15 seconds. Full reserved-view and cam08 rendering occurs after optimization, for each saved checkpoint; these renders restore the appropriate SH degree. Initial duration estimate: 10–20 minutes, depending on startup and hardware load. Existing environments are reused without package installation.

Each execution creates `outputs/fixed-duration-<UTC timestamp>/`. The final `comparison/` contains:

- `test-cam13-comparison.jpg` and `train-cam08-comparison.jpg`: recording / 2,000 / 5,000 / 10,000.
- `progression.png`: full-image and target-changing-region PSNR curves.
- `progression.json` and `.csv`: metrics for all checkpoints, including SSIM and the frozen-time control.

Comparison verifies identical target pixels across checkpoints. The changing-region metric is not board segmentation. Assess whether the board becomes recognizable and its motion improves, alongside the background and frozen-time control. A global score increase alone does not validate the trick. Results from the same trajectory are the primary duration comparison; do not assume a bitwise match with the older run's 2,000-step checkpoint.

Validation completed without optimization: Windows launcher `-CheckOnly`, actual GPU loader/projection check with the inherited configuration, effective-config comparison, checkpoint CLI scheduling tests, and 31 helper tests passed. The comparison/plot pipeline was exercised using baseline images in a fixture layout; **those fixture copies are not 5,000/10,000-step results**. Interrupted runs retain written models/logs; the launcher does not resume optimizer state automatically.
