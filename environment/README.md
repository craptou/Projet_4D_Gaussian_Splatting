# Environment strategy

**Latest target:** after an unsuccessful Colab attempt, the owner selected local WSL2/RTX 4050. Ubuntu 22.04 and a native CUDA 12.1 kernel now work, and PyTorch detects the GPU. Use the [foreground launcher and current status](../docs/progress/local-gpu.en.md) to complete setup and run the bounded experiment. Earlier environment proposals below remain historical; full GPU training has not passed yet.

**20 November 2026:** Colab is now the selected target for the first DyNeRF execution experiment, avoiding WSL installation on the host. The [notebook](../notebooks/dynerf_reference.ipynb) proposes an isolated [Colab environment](environment-colab.yml) with Python 3.10, PyTorch 2.1.2-cu121 and CUDA toolkit 12.1. This compatibility port is unexecuted/unvalidated; it does not replace the exact upstream environment documented below. Windows helper geometry preparation succeeded separately. See the [reference checkpoint](../docs/progress/dynerf.en.md).

Two interpreters serve different purposes. Windows Python 3.11 `.venv` runs capture helpers (Pillow 11.3.0); the upstream research environment uses Python 3.7 and its older dependencies. Do not install the project package, which requires Python >=3.11, into the upstream environment. The scripts themselves use Python-3.7-compatible syntax and bootstrap `src/` directly; training preparation uses that environment's Pillow 9.5.

## Exact upstream reproduction environment

The pinned [official README](https://github.com/hustvl/4DGaussians/tree/843d5ac636c37e4b611242287754f3d4ed150144) specifies Python 3.7 and torch 1.13.1+cu116, torchvision 0.14.1, torchaudio 0.13.1 and mmcv 1.6.0. `environment-upstream.yml` preserves these versions. Upstream leaves ancillary packages unpinned; our dated ancillary pins are a proposed reproducibility specification, **not a verified solver lock or proof of a successful build**. After a successful install, save `conda list --explicit` and `pip freeze` with the experiment artifacts. Do not call it reproduced before the import/training/render checks pass.

Host audit: RTX 4050 Laptop (Ada, compute capability 8.9), 6 GB VRAM, driver 616.56. [NVIDIA's Ada compatibility guide](https://docs.nvidia.com/cuda/ada-compatibility-guide/) states CUDA 11.0–11.7 applications can run on Ada when they include Ampere cubins or PTX. Consequently the GPU alone does **not** prove upstream unusable. CUDA 11.6 cannot compile native sm_89; build extensions with `TORCH_CUDA_ARCH_LIST="8.6+PTX"`. Runtime testing remains required. [PyTorch's version archive](https://pytorch.org/get-started/previous-versions/) confirms the 1.13.1/cu116 distribution. No modern environment file has been invented: there is no demonstrated failure requiring one.

## Windows helpers (already installed and tested)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

FFmpeg and FFprobe must be on PATH. Use the venv Python explicitly; PowerShell activation is optional.

## Recommended training target: WSL2 Ubuntu 22.04

WSL exists but has no Linux distribution. Installing a distribution and OS compiler/CUDA packages is a machine setup step that may require administrator privileges/reboot and interactive user creation. This session did not change Windows features, drivers or boot configuration. Start in PowerShell:

```powershell
wsl --install -d Ubuntu-22.04
```

In WSL, clone the finished repository into the Linux filesystem (`~/skate-trick-4dgs`) for CUDA build performance. Install a user-local Conda distribution using its official installer, then create the environment below. Install Linux build tools including a GCC version supported by CUDA 11.6 (GCC 10 is a conservative target), CMake, Ninja, FFmpeg. Install the **Linux CUDA 11.6 toolkit only**, following [NVIDIA's WSL guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html); keep the Windows NVIDIA driver and do not install a Linux display driver in WSL. `pytorch-cuda` supplies runtime libraries; it does not replace `nvcc`. Verify both toolkit and torch report 11.6 before building.

```bash
git submodule update --init --recursive
conda env create -f environment/environment-upstream.yml
conda activate skate4d-upstream
export TORCH_CUDA_ARCH_LIST='8.6+PTX'
export CC=gcc-10 CXX=g++-10 CUDAHOSTCXX=g++-10
nvcc --version
python -c 'import torch; print(torch.__version__, torch.version.cuda); assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))'
python -m pip install --no-build-isolation -e third_party/4DGaussians/submodules/depth-diff-gaussian-rasterization
python -m pip install --no-build-isolation -e third_party/4DGaussians/submodules/simple-knn
python -c 'import torch, diff_gaussian_rasterization, simple_knn._C; print(torch.cuda.get_arch_list())'
```

These training commands are prepared, **not executed**: no WSL distro, toolkit, compiler environment or PyTorch is installed here. Available VRAM may constrain full-resolution training even if imports work. Start with the bounded official-scene experiment in `docs/experiments.md`; no long training was launched.

## COLMAP

Update 2026-11-18: **PyCOLMAP 4.2.1 CPU sparse mapping now works in the Windows helper `.venv`**. Use `pip install -e ".[sfm]"` or the captured `requirements-sfm-windows.txt` to recreate the local pose-preparation dependencies. This is separate from the old upstream training environment. See `docs/pose-pilot-2026-11-18.md` for the successful real-data pilot. The `colmap` executable and GPU dense stereo are still absent; the initial audit below remains historical.

`colmap -h` was attempted: command absent, CUDA support unverified. The safest Windows path is the prebuilt binary linked by [official installation docs](https://colmap.github.io/install.html), unpacked locally. In WSL a packaged CPU COLMAP is useful for sparse SfM, but distribution packages generally lack CUDA dense stereo. Our upstream-style dense wrapper requires CUDA-capable COLMAP (`patch_match_stereo`). Prefer an official CUDA container or official binary where available before considering a source build. Do not mistake GPU SIFT availability for dense stereo support. Run `colmap -h` and a small actual dense-stereo check, record version/build, and adjust option names if a newer COLMAP release changes them. Wrapper commands follow the inspected legacy upstream CLI and are not yet integration-tested.
