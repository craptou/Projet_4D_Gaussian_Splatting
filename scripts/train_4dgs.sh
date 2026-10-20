#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
name="${1:?Usage: bash scripts/train_4dgs.sh DATASET}"
[[ "$name" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] || { echo 'Invalid dataset name' >&2; exit 1; }
source_path="$ROOT/data/processed/$name"
[[ -f "$source_path/points3D_multipleview.ply" ]] || { echo 'Run preprocessing first' >&2; exit 1; }
[[ ! -e "$ROOT/outputs/$name" ]] || { echo 'Output exists; refusing overwrite' >&2; exit 1; }
cd "$ROOT/third_party/4DGaussians"
python -c 'import torch, diff_gaussian_rasterization, simple_knn._C; assert torch.cuda.is_available()'
echo 'Running bounded smoke training: 2 coarse + 10 fine iterations.'
exec python train.py -s "$source_path" --model_path "$ROOT/outputs/$name" --expname "$name" --configs "$ROOT/configs/experiments/fixed-smoke.py" --save_iterations 10 --test_iterations 10 --ip 127.0.0.1
