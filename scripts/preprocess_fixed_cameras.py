"""Safely stage the inspected upstream COLMAP/LLFF workflow, keeping failure logs."""
import argparse
import json
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import _bootstrap
from skate4d.dataset import ROOT
from make_dataset import stage

LLFF_COMMIT = "c6e27b1ee59cb18f054ccb0f87a90214dbe70482"


def preprocess(name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name):
        raise ValueError("Dataset name must contain only letters, numbers, underscore or hyphen")
    for tool in ("colmap", "git"):
        if not shutil.which(tool):
            raise ValueError(f"Missing {tool}; activate the documented WSL training environment")
    source = ROOT / "data/frames" / name
    target = ROOT / "data/processed" / name
    if target.exists():
        raise ValueError(f"Target already exists: {target}")
    work_root = ROOT / "outputs/preprocess"
    work_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=name+"-", dir=work_root)).resolve()
    print(f"Controlled workspace retained on success/failure: {work}", flush=True)
    upstream = ROOT / "third_party/4DGaussians"
    staged = work / "data/multipleview" / name
    stage(source, staged)
    # Upstream extractimages blindly os.listdir()s every entry, including files.
    # Keep our provenance outside its camera-only input until extraction finishes.
    provenance = work / "capture.json"
    (staged / "capture.json").rename(provenance)
    log = work / "commands.log"

    def run(args):
        print("Running: " + " ".join(map(str, args)), flush=True)
        with log.open("a", encoding="utf-8") as handle:
            handle.write("\nCOMMAND " + repr(list(map(str, args))) + "\n")
            handle.flush()
            subprocess.run(list(map(str, args)), cwd=work, stdout=handle, stderr=subprocess.STDOUT, check=True)

    # extractimages.py uses a relative data/ path and creates colmap_tmp in cwd.
    run([sys.executable, upstream / "scripts/extractimages.py", f"multipleview/{name}"])
    shutil.copy2(provenance, staged / "capture.json")
    tmp = work / "colmap_tmp"
    images, db = tmp / "images", tmp / "database.db"
    # Explicit shared undistorted intrinsics match upstream's cam_intrinsics[1] assumption.
    run(["colmap", "feature_extractor", "--database_path", db, "--image_path", images,
         "--ImageReader.camera_model", "SIMPLE_PINHOLE", "--ImageReader.single_camera", "1"])
    run(["colmap", "exhaustive_matcher", "--database_path", db])
    (tmp / "sparse").mkdir()
    run(["colmap", "mapper", "--database_path", db, "--image_path", images, "--output_path", tmp / "sparse"])
    # Reject incomplete registration: upstream's positional camera mapping would be unsafe.
    # Load the binary reader directly: importing scene would initialize the CUDA model.
    spec = importlib.util.spec_from_file_location("upstream_colmap_reader", upstream / "scene/colmap_loader.py")
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    extrinsics = reader.read_extrinsics_binary(str(tmp / "sparse/0/images.bin"))
    expected = {f"image{i}.jpg" for i in range(1, len(list(staged.glob('cam*')))+1)}
    if {e.name for e in extrinsics.values()} != expected:
        raise ValueError("COLMAP failed to register all training views in model 0")
    shutil.copytree(tmp / "sparse/0", staged / "sparse_")
    run(["colmap", "image_undistorter", "--image_path", images, "--input_path", tmp / "sparse/0", "--output_path", tmp / "dense", "--output_type", "COLMAP"])
    run(["colmap", "patch_match_stereo", "--workspace_path", tmp / "dense", "--workspace_format", "COLMAP", "--PatchMatchStereo.geom_consistency", "true"])
    run(["colmap", "stereo_fusion", "--workspace_path", tmp / "dense", "--workspace_format", "COLMAP", "--input_type", "geometric", "--output_path", tmp / "dense/fused.ply"])
    run([sys.executable, upstream / "scripts/downsample_point.py", tmp / "dense/fused.ply", staged / "points3D_multipleview.ply"])
    run(["git", "clone", "--no-checkout", "https://github.com/Fyusion/LLFF.git", work / "LLFF"])
    run(["git", "-C", work / "LLFF", "checkout", LLFF_COMMIT])
    run([sys.executable, work / "LLFF/imgs2poses.py", tmp])
    shutil.copy2(tmp / "poses_bounds.npy", staged / "poses_bounds_multipleview.npy")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(staged, target)
    print(f"Prepared {target}; holdout excluded. Logs: {log}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dataset")
    args = p.parse_args()
    try:
        preprocess(args.dataset)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        p.exit(1, f"Preprocessing failed: {error}\nAny workspace created is retained under outputs/preprocess.\n")
