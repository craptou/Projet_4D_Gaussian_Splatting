"""Dataset metadata and external command helpers."""
import json
import subprocess
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(args, **kwargs):
    result = subprocess.run([str(a) for a in args], text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise ValueError(f"Command failed ({result.returncode}): {args}\n{result.stderr[-4000:]}")
    return result.stdout


def metadata(path):
    result = json.loads((Path(path) / "metadata.json").read_text(encoding="utf-8"))
    if result.get("camera_motion") not in ("fixed", "moving"):
        raise ValueError("metadata.camera_motion must be fixed or moving")
    if result.get("camera_mode") not in ("fixed", "follow", "orbit", "custom"):
        raise ValueError("metadata.camera_mode must be fixed, follow, orbit or custom")
    if not result.get("replay_id"):
        raise ValueError("A real replay_id is required")
    return result


def probe(video):
    result = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                             "-show_streams", "-show_frames", "-show_entries",
                             "stream=width,height,avg_frame_rate,r_frame_rate:frame=best_effort_timestamp_time",
                             "-of", "json", video]))
    stream = result["streams"][0]
    fps = Fraction(stream["avg_frame_rate"])
    times = [float(f["best_effort_timestamp_time"]) for f in result["frames"]]
    if fps <= 0 or not times:
        raise ValueError(f"No usable frames/FPS in {video}")
    times = [t - times[0] for t in times]
    if any(abs((b-a) - 1/float(fps)) > max(0.0001, 0.01/float(fps))
           for a,b in zip(times, times[1:])):
        raise ValueError(f"Variable/discontinuous frame timing in {video}; align explicitly first")
    return {"fps": str(fps), "resolution": [stream["width"], stream["height"]],
            "count": len(times), "timestamps": times}
