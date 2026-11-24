"""Measure three score-overlay events in the recovered 60-FPS fixed-view clips."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image

FILTER = "crop=1126:500:0:350,scale=563:250"
SIZE = 563 * 250 * 3


def signature(raw):
    image = np.frombuffer(raw, np.uint8).reshape(250, 563, 3).astype(np.int16)
    green = (image[:,:,1] > 180) & (image[:,:,1]-image[:,:,0] > 70) & (image[:,:,1]-image[:,:,2] > 70)
    y, x = np.nonzero(green)
    if len(x) < 10:
        return None
    cropped = green[y.min():y.max()+1, x.min():x.max()+1]
    return np.array(Image.fromarray(cropped).resize((32,32), Image.Resampling.NEAREST))


def check(clips, output):
    if output.exists():
        raise ValueError("Output exists")
    templates = {}
    for label, time in [("manual22", 7), ("manual9", 8), ("hardflip87", 10)]:
        raw = subprocess.check_output(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(time),
            "-i", str(clips/"cam01.mp4"), "-vf", FILTER, "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"])
        templates[label] = signature(raw)
        if templates[label] is None:
            raise ValueError("Missing score template")
    names = json.loads((clips/"cuts.json").read_text())["distinct_sampled_fixed_views"]
    results = []
    for name in names:
        labels, scores = [], []
        process = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", str(clips/(name+".mp4")),
            "-vf", FILTER, "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"], stdout=subprocess.PIPE)
        while True:
            raw = process.stdout.read(SIZE)
            if not raw:
                break
            if len(raw) != SIZE:
                raise ValueError("Partial frame")
            current = signature(raw)
            matches = {} if current is None else {key: float((current & value).sum()/max(1,(current | value).sum())) for key,value in templates.items()}
            key = max(matches, key=matches.get) if matches else None
            value = matches.get(key, 0)
            labels.append(key if value >= .65 else None)
            scores.append(round(value, 3))
        process.stdout.close()
        if process.wait():
            raise RuntimeError("Score decode failed")
        onsets = {}
        for label in templates:
            # Moving antialiased text can briefly reduce mask IoU. Require the
            # current detection and three confirmations in a five-frame window.
            stable = [i for i in range(len(labels)-4) if labels[i] == label and labels[i:i+5].count(label) >= 3]
            if not stable:
                raise ValueError(f"Missing stable {label} in {name}")
            onsets[label] = stable[0]
        results.append(dict(camera_id=name, event_onsets_frames=onsets, classified_frames=labels, template_iou=scores))
        print(name, onsets, flush=True)
    spread = {label:max(r["event_onsets_frames"][label] for r in results)-min(r["event_onsets_frames"][label] for r in results) for label in templates}
    reference = {label:int(np.median([r["event_onsets_frames"][label] for r in results])) for label in templates}
    for result in results:
        offsets = [result["event_onsets_frames"][label]-reference[label] for label in templates]
        result["suggested_source_frame_offset"] = int(np.median(offsets))
        result["offset_disagreement_frames"] = max(offsets)-min(offsets)
    report = dict(fps=60, roi_xywh=[0,350,1126,500], templates_source="cam01 at clip times 7,8,10 seconds; green score masks normalized to 32x32",
        method="Template intersection-over-union >=0.65; onset detected now and in >=3 of the next 5 frames including now", event_spread_frames=spread,
        reference_onsets_frames=reference, cameras=results,
        caution="Three UI event checks, not proof of frame-perfect simulation alignment. Suggested offsets are constant integer-frame shifts; no time warping.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+"\n")
    print("Event spreads:", spread, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clips", type=Path, default=Path("data/raw/true-skate-fixed-2026-11-23"))
    parser.add_argument("--output", type=Path, default=Path("outputs/fixed-dynamic-preparation/events-v2.json"))
    args = parser.parse_args()
    check(args.clips, args.output)
