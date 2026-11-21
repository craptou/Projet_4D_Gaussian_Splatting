"""Select better-supported initialization points using training geometry only.

Images, camera calibration and timestamps are identical to the smoke input.
The selection is a controlled initialization variant, not ground-truth cleanup.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pycolmap


def prepare(source, output, reference):
    if output.exists():
        raise ValueError("Output exists; refusing to change an existing experiment input")
    model = pycolmap.Reconstruction(reference)
    if any(image.name == "cam00.png" for image in model.images.values()):
        raise ValueError("Held-out camera entered initialization geometry")
    selected = [(int(k), p) for k, p in sorted(model.points3D.items())
                if p.track.length() >= 3 and p.error <= 2.0]
    if len(selected) < 1000:
        raise ValueError("Too few supported points; inspect geometry before training")
    output.mkdir(parents=True)
    for file in source.rglob("*"):
        if not file.is_file() or file.name in {"preparation.json", "points3D_downsample2.ply"}:
            continue
        target = output / file.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(file, target)
    xyz = np.array([p.xyz for _, p in selected], dtype=np.float32)
    rgb = np.array([p.color for _, p in selected], dtype=np.uint8)
    vertices = np.zeros(len(xyz), dtype=[(key, "<f4") for key in ["x", "y", "z", "nx", "ny", "nz"]]
                        + [(key, "u1") for key in ["red", "green", "blue"]])
    for i, key in enumerate(["x", "y", "z"]):
        vertices[key] = xyz[:, i]
    for i, key in enumerate(["red", "green", "blue"]):
        vertices[key] = rgb[:, i]
    header = "ply\nformat binary_little_endian 1.0\nelement vertex %d\n" % len(xyz)
    header += "".join("property float %s\n" % key for key in ["x", "y", "z", "nx", "ny", "nz"])
    header += "".join("property uchar %s\n" % key for key in ["red", "green", "blue"])
    (output / "points3D_downsample2.ply").write_bytes((header + "end_header\n").encode() + vertices.tobytes())
    original = np.array([p.xyz for p in model.points3D.values()])
    report = json.loads((source / "preparation.json").read_text())
    report.update(initialization="Training-only sparse map: >=3 observations, mean reprojection <=2px",
        selection=dict(original_points=model.num_points3D(), retained_points=len(selected),
            removed_points=model.num_points3D()-len(selected), minimum_observations=3,
            maximum_mean_reprojection_error_pixels=2.0,
            original_bounds=[original.min(0).tolist(), original.max(0).tolist()],
            selected_bounds=[xyz.min(0).tolist(), xyz.max(0).tolist()],
            selected_point_ids=[k for k, _ in selected],
            reference_points_sha256=hashlib.sha256((reference / "points3D.bin").read_bytes()).hexdigest()),
        purpose="Bounded quality pilot; changed initialization and optimization, not an isolated ablation")
    (output / "preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Selected {len(selected)}/{model.num_points3D()} points; Z maximum {original[:,2].max():.2f} -> {xyz[:,2].max():.2f}")
    print("Images/calibration reused through hard links; cam00 excluded from geometry selection.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/processed/dynerf-local-smoke"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/dynerf-local-quality"))
    parser.add_argument("--reference", type=Path, default=Path("outputs/dynerf-reference/triangulation/sparse"))
    args = parser.parse_args()
    prepare(args.source, args.output, args.reference)
