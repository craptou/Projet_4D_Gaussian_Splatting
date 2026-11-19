# Moving-camera pose pilot — 2026-11-18

## Result

A CPU sparse reconstruction using PyCOLMAP 4.2.1 registered **175/175 sampled images** from **25 replay passages in one model**. The model contains **8767 points**, mean reprojection error **0.473 pixels**, mean track length **6.59 observations**. **8377 points** have observations from two or more passages. Thus the model is linked across views, not merely a collection of unrelated temporal reconstructions. This is training/background-fit evidence, not a held-out score or proof of metrically correct geometry.

Only seven timestamps per passage were reconstructed: zero-based clip indices `[0,18,36,54,72,90,108]`, at 30 FPS. `cam07` is reserved as a provisional holdout and excluded from feature extraction, matching and mapping. No final game replay ID or precise azimuths have been invented. The current result does not provide poses for the other 102 frames per passage or for cam07.

The first pilot used six passages/42 images and registered 33, with 1651 points and 0.403 px mean reprojection error. Adding the available intermediate passages resolved the incomplete registration without weakening the mapper's pose/reprojection thresholds. The expanded command exited successfully (code 0), elapsed about 101.5 seconds including feature extraction/matching/mapping. No GPU training was performed.

## Preparation and calibration assumptions

Images are decoded directly from the original 118.633-second recording using the documented source frame indices, avoiding another lossy round trip through the cut MP4s. The common crop is original `(x=64,y=100,width=592,height=820)` with no resizing. It removes the side bars, REPLAY title, and bottom controls. Features are excluded in source-coordinate rectangles `[200,440,590,860]` (board and approximate shadow area) and `[64,180,656,350]` (possible score overlay). Images themselves are not blacked out: the binary mask only controls SIFT extraction. Conservative rectangles can hide useful static content and require review on different captures.

Shared `SIMPLE_PINHOLE` intrinsics are a hypothesis for this capture, not ground truth. The original image center is assumed to be `(360,640)`; after the crop the principal point is fixed at `(296,540)`, not the cropped image center. The focal length is optimized from a heuristic initialization of 984 px; the expanded fit gives **443.825 px**. No lens distortion is estimated. A future variable-FOV or off-center game camera would invalidate this assumption and require a richer model. Extrinsics are **world-to-camera** `[R|T]`; exported centers and point clouds share an arbitrary SfM scale/gauge. Rotation orthonormality was checked to numerical precision.

Each image has its own estimated pose, even though intrinsics are shared. Exported pose records retain passage ID, source frame index, clip frame index, relative time and split. All 25 sampled trajectories have nonzero recovered camera-center motion; their shapes and similar travel lengths are consistent with a repeated followed replay. This consistency is not ground-truth trajectory validation.

## Synchronization check

The green trick score becomes visible persistently at zero-based clip frame **97 or 98** in **26/26** clips: an onset spread of **one 30-FPS frame (~33 ms)**. `scripts/check_replay_sync.py` saves the per-frame counts and event detections. This is a second check alongside timeline-cursor fitting and the board-motion contact sheets. The detector is specific to the visible bright green overlay and capture dimensions, not a general action recognizer. No offsets were applied and no clip was overwritten. One common UI event does not certify synchronization over the complete replay or detect every skipped simulation frame.

An exploratory audio-envelope check did not provide usable repeated event evidence, so no audio-based synchronization correction was made. Its diagnostic JSON is retained under outputs/capture-inspection; near-zero correlations should not be treated as valid offsets.

## Reproduce

The official [PyCOLMAP documentation](https://colmap.github.io/pycolmap/index.html) describes the sparse pipeline; [mask semantics](https://colmap.github.io/pycolmap/pycolmap.html#pycolmap.ImageReaderOptions.camera_mask_path) use black pixels to suppress features. A prebuilt Python wheel was installed in project-local `.venv`; no CUDA, WSL, OS driver, upstream submodule or system compiler was changed. `pycolmap.has_cuda` reports false; CPU SIFT and sparse mapping worked. This does not install a `colmap` command or CUDA dense stereo.

```powershell
.\.venv\Scripts\python.exe -m pip install -r environment/requirements-sfm-windows.txt
.\.venv\Scripts\python.exe scripts/check_replay_sync.py
.\.venv\Scripts\python.exe scripts/prepare_pose_probe.py --config configs/datasets/replay-pose-expanded.json --output data/processed/replay-pose-expanded
.\.venv\Scripts\python.exe scripts/estimate_pose_probe.py --dataset data/processed/replay-pose-expanded --output outputs/replay-pose-expanded
.\.venv\Scripts\python.exe scripts/analyze_pose_probe.py outputs/replay-pose-expanded
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Preparation, sync reports and reconstruction refuse existing destinations; choose fresh paths to rerun. Analyze regenerates only its own figure/geometry-check files. The recorded expanded process sent stdout/stderr to `outputs/pose-expanded-run.log`. Configuration snapshots and timing are in the run report. Mapping is capped at 180 seconds, four CPU threads, at most three models; features are capped at 2048 per image. No algorithm or dependency upgrade was made to upstream 4DGS. Nineteen helper tests pass, including real FFmpeg extraction, source-index preservation, crop/mask coordinates and held-out exclusion.

## Artifacts (ignored by Git)

- `data/processed/replay-pose-expanded/`: original-derived PNG samples, binary background mask, image/source/time manifest, masked and unmasked contact sheets.
- `outputs/replay-pose-expanded/sparse/0/`: native sparse reconstruction.
- `outputs/replay-pose-expanded/model-0.ply`: sparse colored static-background point cloud.
- `outputs/replay-pose-expanded/poses-model-0.json`: per-sample world-to-camera poses and shared intrinsics.
- `outputs/replay-pose-expanded/report.json`, `geometry-checks.json`: registration, reprojection and cross-passage track counts.
- `outputs/replay-pose-expanded/geometry-and-trajectories.png` and `.svg`: point cloud and camera travel plot; 1% per-axis point-cloud tails hidden for readability, full PLY retained.
- `outputs/capture-inspection/score-sync-check.json`: green-score onset diagnostic.

## Remaining gates

This establishes that static-background SfM is feasible on the sampled moving-camera capture. It does not reconstruct the moving board. Before 4DGS training: reproduce upstream on official data, estimate/validate the remaining per-frame poses, inspect difficult fast-motion frames and changing intrinsics, localize cam07 against the training background without adding it to optimization, and validate the proposed per-frame pose loader/converter. Do not run these images through the fixed MultipleView loader. Sparse masks are for calibration; they must not permanently remove the board from future dynamic scene training.
