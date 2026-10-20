"""Strict synchronized frame validation."""
import json
import re
from fractions import Fraction
from pathlib import Path
from PIL import Image
from .dataset import metadata


def validate(path):
    path = Path(path)
    meta = metadata(path)
    manifest = json.loads((path / "extraction.json").read_text(encoding="utf-8"))
    cameras = sorted(p for p in path.glob("cam*") if p.is_dir())
    if len(cameras) < 3:
        raise ValueError("Need at least two training cameras and one holdout")
    holdout = meta.get("holdout_camera")
    if holdout not in [p.name for p in cameras]:
        raise ValueError("Declare an existing holdout_camera (e.g. cam_holdout or cam07)")
    counts, sizes, rates = [], set(), set()
    if set(manifest["cameras"]) != {p.name for p in cameras}:
        raise ValueError("Camera directories differ from extraction manifest")
    indices = manifest["source_frame_indices"]
    if not indices or indices[0] < 1 or any(b <= a for a,b in zip(indices, indices[1:])):
        raise ValueError("Invalid common source frame indices")
    for cam in cameras:
        files = sorted(cam.iterdir())
        if any(not re.fullmatch(r"frame_\d{5}\.jpg", p.name) for p in files):
            raise ValueError(f"Unexpected filename in {cam.name}")
        expected = [f"frame_{i:05d}.jpg" for i in range(1, len(files)+1)]
        if not files or [p.name for p in files] != expected:
            raise ValueError(f"Missing or nonconsecutive frames in {cam.name}")
        info = manifest["cameras"][cam.name]
        fps = Fraction(info["fps"])
        if fps <= 0:
            raise ValueError(f"Invalid FPS: {cam.name}")
        rates.add(str(fps))
        if indices[-1] > info["count"]:
            raise ValueError(f"Source index exceeds recorded count: {cam.name}")
        if info["extracted_count"] != len(files) or len(indices) != len(files):
            raise ValueError(f"Manifest count mismatch: {cam.name}")
        for file in files:
            with Image.open(file) as im:
                im.verify()
            with Image.open(file) as im:
                sizes.add(im.size)
                if list(im.size) != info["resolution"]:
                    raise ValueError(f"Manifest resolution mismatch: {file}")
        counts.append(len(files))
    if len(set(counts)) != 1 or len(sizes) != 1 or len(rates) != 1:
        raise ValueError("Frame count, resolution or source FPS differs between cameras")
    if meta.get("fps") is not None and Fraction(str(meta["fps"])) != Fraction(next(iter(rates))):
        raise ValueError("Declared FPS differs from manifest")
    if meta.get("resolution") is not None and tuple(meta["resolution"]) != next(iter(sizes)):
        raise ValueError("Declared resolution differs from manifest")
    return {"cameras": len(cameras), "frames_per_camera": counts[0], "resolution": list(sizes)[0],
            "source_fps": next(iter(rates)), "camera_motion": meta["camera_motion"],
            "holdout": holdout, "synchronization": "Timing verified; replay state requires visual inspection"}
