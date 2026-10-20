"""Extract common source indexes without independently resampling videos."""
import argparse
import json
from fractions import Fraction
from pathlib import Path
import _bootstrap
from skate4d.dataset import metadata, probe, run
from skate4d.validation import validate


def extract(source, output, interval=1):
    source, output = Path(source).resolve(), Path(output).resolve()
    if interval < 1:
        raise ValueError("--interval must be a positive integer")
    meta = metadata(source)
    videos = sorted(source.glob("cam*.mp4"))
    if len(videos) < 3:
        raise ValueError("Need at least three cam*.mp4 videos including the holdout")
    infos = {v.stem: probe(v) for v in videos}
    ref = next(iter(infos.values()))
    for name, info in infos.items():
        if any(info[k] != ref[k] for k in ("fps", "resolution", "count")):
            raise ValueError(f"{name}: source FPS/resolution/frame count mismatch; align videos explicitly")
        if any(abs(a-b) > 0.0001 for a,b in zip(info["timestamps"], ref["timestamps"])):
            raise ValueError(f"{name}: source timestamp mismatch")
    if meta.get("fps") is not None and Fraction(str(meta["fps"])) != Fraction(ref["fps"]):
        raise ValueError("Declared FPS differs from videos")
    if meta.get("resolution") is not None and meta["resolution"] != ref["resolution"]:
        raise ValueError("Declared resolution differs from videos")
    if output.exists():
        raise ValueError(f"Output already exists; choose a new directory: {output}")
    if meta.get("holdout_camera") not in infos:
        raise ValueError("metadata.holdout_camera must name an input video stem")
    output.mkdir(parents=True)
    (output / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    indices = list(range(1, ref["count"]+1, interval))
    for video in videos:
        target = output / video.stem
        target.mkdir()
        run(["ffmpeg", "-nostdin", "-v", "error", "-i", video, "-map", "0:v:0",
             "-vf", f"select=not(mod(n\\,{interval}))", "-fps_mode", "passthrough",
             "-q:v", "2", "-start_number", "1", target / "frame_%05d.jpg"])
        infos[video.stem]["extracted_count"] = len(list(target.glob("*.jpg")))
        infos[video.stem].pop("timestamps")
    manifest = {"schema_version": 1, "interval": interval, "source_frame_indices": indices,
                "cameras": infos}
    (output / "extraction.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return validate(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--interval", type=int, default=1, help="Take every Nth source frame in all views")
    args = parser.parse_args()
    try:
        print(json.dumps(extract(args.input, args.output, args.interval), indent=2))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"ERROR: {error}\nPartial output, if present, is retained for inspection.\n")
