"""Stage only training views under upstream-compatible contiguous names."""
import argparse
import json
import shutil
from pathlib import Path
import _bootstrap
from skate4d.dataset import metadata
from skate4d.validation import validate
from skate4d.cameras import require_fixed


def stage(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    validate(source)
    meta = metadata(source)
    require_fixed(meta)
    if target.exists():
        raise ValueError(f"Refusing to overwrite {target}")
    cameras = sorted(d for d in source.glob("cam*") if d.is_dir() and d.name != meta["holdout_camera"])
    target.mkdir(parents=True)
    mapping = {}
    for i, camera in enumerate(cameras, 1):
        name = f"cam{i:02d}"
        shutil.copytree(camera, target / name)
        mapping[name] = camera.name
    (target / "capture.json").write_text(json.dumps({"camera_motion": "fixed", "train_mapping": mapping,
        "holdout_camera": meta["holdout_camera"], "heldout_images_in_training": False}, indent=2), encoding="utf-8")
    return mapping


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("target", type=Path)
    args = p.parse_args()
    try:
        print(stage(args.source, args.target))
    except (ValueError, OSError, KeyError) as error:
        p.exit(1, f"ERROR: {error}\n")
