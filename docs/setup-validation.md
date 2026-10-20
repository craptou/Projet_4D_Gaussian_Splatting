# Setup validation — 2026-10-19

## Executed successfully

- `git submodule update --init --recursive`: upstream, rasterizer, simple-knn and rasterizer's GLM initialized at the recorded gitlink SHAs. Upstream working tree unchanged.
- `python -m venv .venv`; `.venv\Scripts\python.exe -m pip install -e .`: helper package/Pillow installed locally.
- `.venv\Scripts\python.exe -m unittest discover -s tests -v`: **12 tests passed**, no skipped FFmpeg tests. Includes a generated 6-FPS, 6-frame, 64x48 video replicated into three synchronized views, interval-2 extraction (source indexes 1/3/5), rejected 5-FPS replacement, no-overwrite behavior, missing/nonnumeric names, manifest FPS/count checks, resolution/holdout/motion checks, contact sheet generation and holdout-safe staging. Synthetic media exist only inside disposable test-owned temporary directories.
- `.venv\Scripts\python.exe -m pip check`: no broken requirements.
- Git Bash `bash -n` on all three shell wrappers: syntax passed.
- `.venv\Scripts\python.exe -m compileall -q scripts src tests configs`: passed.
- Invalid preprocessing name `../unsafe` fails before creating output. Missing COLMAP fails with actionable error. These expected failures are preflight validation, not successful preprocessing.
- `.venv\Scripts\python.exe scripts/check_system.py`: report written, including attempted absent tool commands and PyTorch import failure.
- Official D-NeRF HTTP HEAD: archive size measured without downloading dataset body.
- Portable GitHub CLI checksum verified against official release checksum manifest. `auth status`: no authenticated host.

## Not executed / not passed

No Linux distro, Conda environment solve, CUDA toolkit install, CUDA extension compilation, torch GPU execution, COLMAP sparse/dense reconstruction, official sample download, official-scene training/rendering, True Skate training, moving-camera adapter or held-out metrics. Training environment YAML is a proposed version specification rather than a validated lockfile. Legacy COLMAP and LLFF commands must be integration-tested in the documented Linux environment. The setup remains blocked at GPU reproduction, with the independent capture-helper work complete.
