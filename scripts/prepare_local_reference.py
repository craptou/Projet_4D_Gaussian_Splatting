"""Prepare a small, contiguous DyNeRF execution test for a 6 GB GPU.

Keeps the first 30 frames and supplied calibration for four train views and
cam00. Uses the already downloaded official videos; no network access.
"""
import argparse
import json
import os
import subprocess
from pathlib import Path

import numpy as np


def prepare(source, output):
    if output.exists():
        raise ValueError("Output exists; choose a fresh destination")
    videos = sorted(source.glob("cam*.mp4"))
    calibration = np.load(source / "poses_bounds.npy", allow_pickle=False)
    if calibration.shape != (len(videos), 17):
        raise ValueError("Video/calibration count mismatch")
    selected = ["cam00", "cam01", "cam05", "cam12", "cam20"]
    rows = [next(i for i, video in enumerate(videos) if video.stem == name) for name in selected]
    output.mkdir(parents=True)
    np.save(output / "poses_bounds.npy", calibration[rows])
    for row in rows:
        video = videos[row]
        # A same-volume hard link avoids duplicating the existing videos.
        os.link(video, output / video.name)
        images = output / video.stem / "images"
        images.mkdir(parents=True)
        subprocess.run(["ffmpeg", "-v", "error", "-threads", "2", "-i", str(video),
            "-vf", "scale=1352:1014", "-frames:v", "30", "-start_number", "0",
            "-compression_level", "3", str(images / "%04d.png")], check=True)
        if len(list(images.glob("*.png"))) != 30:
            raise ValueError("Incomplete frame extraction")
    root = Path(__file__).resolve().parents[1]
    cloud = np.load(root / "docs/evidence/dynerf-reference-init.npz", allow_pickle=False)
    xyz, rgb = cloud["xyz"], cloud["rgb"]
    vertices = np.zeros(len(xyz), dtype=[(key, "<f4") for key in ["x", "y", "z", "nx", "ny", "nz"]]
                        + [(key, "u1") for key in ["red", "green", "blue"]])
    for i, key in enumerate(["x", "y", "z"]):
        vertices[key] = xyz[:, i]
    for i, key in enumerate(["red", "green", "blue"]):
        vertices[key] = rgb[:, i]
    header = "ply\nformat binary_little_endian 1.0\nelement vertex %d\n" % len(xyz)
    header += "".join("property float %s\n" % key for key in ["x", "y", "z", "nx", "ny", "nz"])
    header += "".join("property uchar %s\n" % key for key in ["red", "green", "blue"])
    with (output / "points3D_downsample2.ply").open("wb") as handle:
        handle.write((header + "end_header\n").encode("ascii"))
        handle.write(vertices.tobytes())
    report = dict(source_scene=source.name, camera_ids=selected, source_calibration_rows=rows,
        train_cameras=selected[1:], heldout_camera="cam00", source_frames=list(range(30)),
        training_images=120, test_images=30, image_resolution=[1352, 1014],
        time_rule="frame_index / 300, unchanged from the original 300-frame scene",
        initialization="3390 sparse points from frame 0 of all 19 original training cameras; cam00 excluded",
        purpose="Reduced execution test, not full DyNeRF reproduction or quality benchmark",
        dataset_license="CC-BY-NC-4.0; Neural 3D Video Synthesis, Li et al., CVPR 2022")
    (output / "preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/sample/dynerf/cut_roasted_beef"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/dynerf-local-smoke"))
    args = parser.parse_args()
    prepare(args.source, args.output)
