#!/usr/bin/env bash
# Run inside Ubuntu 22.04 WSL2 as root. Installs no Linux display driver.
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Run with wsl -d Ubuntu-22.04 -u root.' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
export PIP_PROGRESS_BAR=off
echo '[INSTALLATION] Outils Ubuntu et compilateur CUDA'
apt-get update -qq
apt-get install -y --no-install-recommends python3-venv python3-dev python3-tk \
    gcc g++ ninja-build cmake curl ca-certificates ffmpeg libgl1 libglib2.0-0
if ! dpkg-query -W cuda-keyring >/dev/null 2>&1; then
    curl --fail --location --output /tmp/skate4d-cuda-keyring.deb \
        https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
    dpkg -i /tmp/skate4d-cuda-keyring.deb
fi
apt-get update -qq
# The compiler, headers and CUB/Thrust are sufficient for these extensions.
# No cuda / cuda-drivers meta-package, profiler, or full toolkit installation.
apt-get install -y --no-install-recommends cuda-nvcc-12-1 cuda-cudart-dev-12-1 cuda-cccl-12-1
apt-get clean
GPU_ENV=/opt/skate4d/venv
[[ -x "$GPU_ENV/bin/python" ]] || python3 -m venv "$GPU_ENV"
"$GPU_ENV/bin/python" -m pip install --no-cache-dir pip==24.0 setuptools==69.5.1 wheel
echo '[INSTALLATION] PyTorch : reutilisation du telechargement existant si possible'
if ! "$GPU_ENV/bin/python" -c 'import torch; assert torch.__version__.startswith("2.1.2") and torch.version.cuda == "12.1"' >/dev/null 2>&1; then
    mkdir -p /opt/skate4d/cache
    wheel=/opt/skate4d/cache/torch-2.1.2+cu121-cp310-cp310-linux_x86_64.whl
    if [[ ! -f "$wheel" ]] || [[ $(stat -c%s "$wheel") != 2200673027 ]]; then
        existing=$(find /tmp -maxdepth 3 -type f -name 'torch-2.1.2+cu121-cp310-cp310-linux_x86_64.whl' -size 2200673027c -print -quit)
        if [[ -n "$existing" && ! -f "$wheel" ]]; then
            ln "$existing" "$wheel"
        else
            curl --fail --location --continue-at - --output "$wheel" \
                'https://download.pytorch.org/whl/cu121/torch-2.1.2%2Bcu121-cp310-cp310-linux_x86_64.whl'
        fi
    fi
    "$GPU_ENV/bin/python" -m pip install --no-cache-dir --force-reinstall --no-deps "$wheel"
fi
"$GPU_ENV/bin/python" -m pip install --no-cache-dir torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu121
echo '[INSTALLATION] Bibliotheques du projet'
"$GPU_ENV/bin/python" -m pip install --no-cache-dir numpy==1.26.4 Pillow==9.5.0 \
    opencv-python-headless==4.9.0.80 yapf==0.40.1 scipy==1.11.4 matplotlib==3.7.5 \
    lpips==0.1.4 plyfile==1.0.3 pytorch-msssim==1.0.0 open3d==0.18.0 \
    imageio==2.31.2 imageio-ffmpeg==0.4.9 scikit-image==0.21.0 tqdm==4.66.1 tensorboard==2.15.2
"$GPU_ENV/bin/python" -m pip install --no-cache-dir mmcv==1.6.0
"$GPU_ENV/bin/python" -m pip check
"$GPU_ENV/bin/python" -c 'import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))'
/usr/local/cuda-12.1/bin/nvcc --version
echo '[INSTALLATION TERMINEE] Python, PyTorch et CUDA sont prets'
