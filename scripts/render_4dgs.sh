#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
name="${1:?Usage: bash scripts/render_4dgs.sh DATASET}"
[[ "$name" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] || { echo 'Invalid dataset name' >&2; exit 1; }
[[ -f "$ROOT/outputs/$name/cfg_args" ]] || { echo 'No trained model found' >&2; exit 1; }
cd "$ROOT/third_party/4DGaussians"
exec python render.py --model_path "$ROOT/outputs/$name" --configs "$ROOT/configs/experiments/fixed-smoke.py" --skip_train --skip_video --iteration 10
