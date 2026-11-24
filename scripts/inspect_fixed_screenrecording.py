"""Inspect this portrait True Skate recording using its replay UI, in seconds.

The UI ROI is measured on 1126x2436 footage. Analysis is sampled at 10 FPS;
this does not assert that the variable-rate source is constant-rate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np


def marker(image):
    bright = image[10:18, 20:220].min(axis=2) > 145
    score = bright.sum(axis=0)
    selected = np.flatnonzero(score >= 3)
    runs = np.split(selected, np.where(np.diff(selected) > 1)[0]+1)
    runs = [run for run in runs if 6 <= len(run) <= 17]
    if not runs:
        return None
    best = max(runs, key=lambda run: score[run].sum())
    return float((best[0]+best[-1])/2+20)


def inspect(source, output):
    output.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-nostdin", "-v", "error", "-hwaccel", "cuda", "-i", str(source),
        "-vf", "fps=10,crop=1000:280:64:2128,scale=250:70:flags=area", "-an",
        "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"]
    records = []
    start = time.monotonic()
    with (output/"ui-decode.log").open("wb") as log:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=log)
        size = 250*70*3
        while True:
            data = process.stdout.read(size)
            if not data:
                break
            if len(data) != size:
                raise ValueError("Partial UI frame")
            image = np.frombuffer(data, np.uint8).reshape(70,250,3).astype(np.int16)
            back, share = image[35:55,5:70], image[35:55,95:160]
            red = float(((back[:,:,0]>back[:,:,1]+35)&(back[:,:,0]>back[:,:,2]+35)).mean())
            teal = float(((share[:,:,1]>share[:,:,0]+35)&(share[:,:,2]>share[:,:,0]+25)).mean())
            is_replay = red > .4 and teal > .4
            x = marker(image) if is_replay else None
            records.append(dict(t=len(records)/10, replay=is_replay, marker=x,
                                red_fraction=round(red,3), teal_fraction=round(teal,3)))
            if len(records)%600 == 0:
                print(f"Inspected {len(records)/10:.0f}s of source", flush=True)
        if process.wait() != 0:
            raise RuntimeError("UI decode failed; see ui-decode.log")
    with source.open("rb") as handle:
        fingerprint = hashlib.file_digest(handle,"sha256").hexdigest()
    report = dict(source=source.name, source_sha256=fingerprint, analysis_fps=10,
        ui_roi_xywh=[64,2128,1000,280], analysis_dimensions=[250,70],
        source_timing="Variable-rate capture; UI analysis sampled by timestamp, not source frame index",
        elapsed_seconds=time.monotonic()-start, records=records)
    (output/"ui-trace.json").write_text(json.dumps(report,indent=2)+"\n")
    # List UI-visible intervals, bridging detector gaps shorter than half a second.
    active = np.array([r["replay"] for r in records])
    for i in range(1,len(active)-1):
        if not active[i] and active[max(0,i-2):i].any() and active[i+1:i+3].any():
            active[i] = True
    edges = np.diff(np.r_[False,active,False].astype(int))
    intervals = [(int(a),int(b)) for a,b in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1))]
    print("Replay UI intervals:",[(a/10,b/10) for a,b in intervals if b-a>=10],flush=True)
    print("Marker observations:",sum(r['marker'] is not None for r in records),flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("outputs/fixed-capture-review"))
    args = parser.parse_args()
    inspect(args.source, args.output)
