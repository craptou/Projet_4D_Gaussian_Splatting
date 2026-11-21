"""Render a checkpoint with the SH degree active during its original training.

Upstream load_ply forces maximum degree, even for early checkpoints. The degree
below follows the pinned from-scratch training schedule (one increase per 1000
steps in each stage). The upstream source and saved models remain untouched.
"""
from argparse import ArgumentParser
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "third_party/4DGaussians"))
import mmcv
import torch
from arguments import ModelParams, ModelHiddenParams, PipelineParams, get_combined_args
from utils.params_utils import merge_hparams
from scene import Scene, GaussianModel
from render import render_set


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    model_params = ModelParams(parser, sentinel=True)
    hidden = ModelHiddenParams(parser)
    pipeline = PipelineParams(parser)
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--coarse-steps", type=int, required=True)
    parser.add_argument("--configs", required=True)
    parser.add_argument("--render-output", type=Path, required=True)
    args = get_combined_args(parser)
    args = merge_hparams(args, mmcv.Config.fromfile(args.configs))
    with torch.no_grad():
        dataset = model_params.extract(args)
        gaussians = GaussianModel(dataset.sh_degree, hidden.extract(args))
        scene = Scene(dataset, gaussians, load_iteration=args.iteration, shuffle=False)
        loaded_degree = gaussians.active_sh_degree
        gaussians.active_sh_degree = min(gaussians.max_sh_degree,
            args.coarse_steps // 1000 + args.iteration // 1000)
        print(f"SH degree restored: {loaded_degree} -> {gaussians.active_sh_degree}", flush=True)
        background = torch.tensor([1, 1, 1] if dataset.white_background else [0, 0, 0],
                                  dtype=torch.float32, device="cuda")
        render_set(str(args.render_output), "test", args.iteration, scene.getTestCameras(),
                   gaussians, pipeline.extract(args), background, scene.dataset_type)
        (args.render_output / "render-settings.json").write_text(json.dumps(dict(
            iteration=args.iteration, coarse_steps=args.coarse_steps,
            upstream_loaded_sh_degree=loaded_degree, active_sh_degree=gaussians.active_sh_degree,
            reason="Match the pinned from-scratch training SH schedule"), indent=2) + "\n")
