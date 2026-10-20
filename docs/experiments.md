# Experiments and reproduction gate

## M0: official-scene smoke reproduction (required before True Skate training)

Use D-NeRF `bouncingballs`, the synthetic example explicitly documented by upstream, with its existing configuration. No COLMAP is needed for that dataset. The [official D-NeRF repository](https://github.com/albertpumarola/D-NeRF) supplies a combined archive, not a verified tiny per-scene download. A HEAD request to its official Dropbox link (`https://www.dropbox.com/s/0bf6fl0ye2vz3vr/data.zip?dl=1`) on 2026-10-19 returned HTTP 200, `Content-Length: 257793177` (**245.85 MiB**). We have not established which scene has the smallest compressed size. No dataset body was downloaded: the archive is substantial and this machine cannot currently run the training environment. Obtain this archive only after reviewing its size, then extract only `bouncingballs` into `data/sample/bouncingballs`. Do not substitute an unverified mirror or call generated helper videos an upstream reproduction.

After the environment import/build gates pass, run from repository root in WSL:

```bash
ROOT="$PWD"
cd third_party/4DGaussians
python train.py -s "$ROOT/data/sample/bouncingballs" --eval --model_path "$ROOT/outputs/dnerf-smoke" --expname dnerf-smoke --configs "$ROOT/configs/experiments/dnerf-smoke.py" --save_iterations 10 --test_iterations 10 --ip 127.0.0.1
python render.py --model_path "$ROOT/outputs/dnerf-smoke" --configs "$ROOT/configs/experiments/dnerf-smoke.py" --iteration 10 --skip_train --skip_video
```

The smoke config limits coarse/fine stages to 2/10 iterations and disables densification. This only proves execution; it cannot establish quality. `--eval` is essential because the synthetic loader otherwise merges test views into training. Keep official train/test split intact. Renderer runs only test views, avoiding the generated 160-frame trajectory. It may still consume memory because upstream stores rendered frames; stop if VRAM is exhausted rather than launching longer training.

Pass gates separately: torch sees GPU; both CUDA modules import; official data loads; coarse/fine training finishes; fine iteration-10 point cloud/deformation artifacts exist; renderer produces nonempty test images. Save exact commands, terminal logs, solver freeze, upstream commit, data provenance and elapsed time. README currently marks all GPU gates **not run**, not passed. Upstream's README warning about Blender data remains an unresolved risk until this actual test succeeds.

## M1: deterministic replay and fixed-camera feasibility

Verify the same replay state at each common source index and confirm background landmarks remain stationary within each camera sequence. Moving camera capture triggers the research branch in `moving-camera-plan.md`; it must not enter MultipleView.

## M2: first custom fixed-camera execution

Extract, validate, inspect sheets, preprocess with COLMAP, inspect calibration, and run the bounded wrapper. Preprocessing needs matching fixed centered intrinsics and a CUDA-enabled dense COLMAP build. Record registration completeness and reprojection error. Coplanar scene structure or only two viewpoints may be inadequate even if the metadata validator passes. Full training is a separate experiment after this smoke gate.

## M3: held-out camera evaluation

Declare cam01–cam06 as training and cam07 (or cam_holdout) as the held-out game view. Stage only training images for optimization and initial reconstruction. Save original/staged camera mapping. The unmodified MultipleView test split repeats training cameras at three timestamps; it is **not scientific held-out evaluation**. Current render wrapper is only a pipeline sanity check, not a held-out metric pipeline.

Later estimate holdout pose by localization against the fixed training reconstruction using its static background (or known game calibration), without adding holdout image colors/dynamic content to optimization. Preserve calibration provenance and disclose any calibration use of holdout images. Supply holdout cameras/timestamps explicitly through a reviewed adapter. At each matched replay time render cam07 and compare against its actual game image. Freeze model and hyperparameters before inspecting holdout scores.

Report PSNR, SSIM and LPIPS on identical dimensions, crop, color space and background treatment. Document metric implementations, range, LPIPS network/version, full-frame versus foreground masks, per-frame values and aggregate mean/spread. Include synchronized qualitative comparisons. No metric implementation or true holdout renderer is included in the initial setup.

## Run record template

Run ID; date; dataset/replay ID; camera motion; train/holdout IDs; synchronization review; image encoding; time normalization; COLMAP model/settings/errors; point-cloud provenance; upstream SHA; environment freeze; config SHA; seed; actual commands; hardware/VRAM; stage duration; output paths; outcome/failure; next justified change.
