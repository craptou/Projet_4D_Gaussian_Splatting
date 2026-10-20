# Decision log — 2026-10-19

- Use the current workspace root (`projet`) as the repository root, as requested; project/package/GitHub name is `skate-trick-4dgs`. No extra nested project folder.
- Pin official hustvl/4DGaussians at `843d5ac636c37e4b611242287754f3d4ed150144`; initialize rasterizer, simple-knn and GLM recursively without edits. Upstream root LICENSE.md is Apache-2.0; nested source notices/dependency licenses still apply. Project wrapper files use Apache-2.0 (LICENSE).
- Direct source inspection confirms fixed extrinsics, first-frame-only calibration, shared single-focal intrinsics and train/test camera overlap. Reject moving captures at staging; no algorithm/loader modification during initial setup.
- Preserve upstream Python 3.7, torch 1.13.1, CUDA 11.6. Ada backward compatibility via Ampere/PTX prevents a claim that this GPU requires all-new dependencies. Propose `8.6+PTX` extension build and verify later; do not declare a successful build.
- Prefer WSL2 for Linux CUDA/Bash tooling. No distro exists, toolkit/compiler/Conda/PyTorch are absent; installing a working OS/CUDA environment would require machine-level provisioning. Finish independently testable Windows helpers now. Do not install gigabytes of Windows torch without a CUDA build toolchain.
- Install Pillow and an editable helper package only into project-local `.venv`. Install GitHub CLI 2.102.0 only into ignored `.tools/gh`, verify SHA256 against release checksums, leave global PATH untouched. `gh auth status` reports no authenticated host; private repository creation/push and optional issues remain pending authentication.
- Require strict matching frame count/FPS/resolution/timestamps before extraction. Interval selects common source indexes; output is contiguous. Visual synchronization remains mandatory because video timing does not prove deterministic game time.
- Replace the unsafe upstream shell orchestration with a retained unique workspace, checked subprocesses and no directory deletion. Use inspected upstream extraction/downsampling, shared SIMPLE_PINHOLE COLMAP, and LLFF pinned at `c6e27b1ee59cb18f054ccb0f87a90214dbe70482`. No runtime pip install or floating LLFF checkout.
- Reserve holdout before staging; prohibit holdout image leakage into optimization. Real held-out rendering remains future adapter work. Do not confuse upstream's training-view test samples with held-out evaluation.
- Official D-NeRF archive size checked by HEAD: 257793177 bytes, not downloaded. Prepare bounded 2-coarse/10-fine reproduction commands; no official data/GPU training has run.

## Failures and resolution

- `gh --version` / `gh auth status`: command not found initially. Small reversible fix: verified portable CLI; status now explicitly unauthenticated. User login is still required; no credentials printed.
- `nvcc --version`, `colmap -h`, torch package inspection: toolkit, COLMAP and torch absent. Root cause is missing training prerequisites, not an observed model incompatibility. Installation/reproduction gates documented in environment/README.md.
- `wsl --list --verbose`: no installed distributions. Prefer explicit Ubuntu provisioning over silently modifying Windows features.
- Initial license copy used `LICENSE` but upstream filename is `LICENSE.md`; copy corrected. No upstream files changed. Commits were separated by dependency, scaffold, helpers and documentation.
- Review found upstream `extractimages.py` assumes every dataset-root entry is a camera directory. Keep our `capture.json` provenance outside its input during extraction, then copy it back. This prevents a NotADirectoryError without editing upstream.
- Validation completed: 12 helper tests including real FFmpeg passed, pip check passed, shell syntax and Python compilation passed. See setup-validation.md for executed commands and explicit unexecuted GPU gates.
