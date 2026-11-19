"""Propose/batch-cut True Skate replay passages using the visible timeline knob.

Default ROI is measured on the supplied 720x1280 capture, not a universal game UI.
Outputs are candidates: UI alignment does not prove frame-perfect game-state sync.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import _bootstrap
from skate4d.dataset import run, probe
from skate4d.replays import slider_center, passage_boundaries, fit_passage


def split(source, output, roi, low, high, execute):
    source = source.resolve()
    if output.exists():
        raise ValueError("Output exists; choose a new directory")
    if not source.is_file():
        raise ValueError(f"Missing recording: {source}")
    info = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=width,height,r_frame_rate,avg_frame_rate", "-of", "json", source]))["streams"][0]
    from fractions import Fraction
    fps = Fraction(info["avg_frame_rate"])
    if fps <= 0 or fps != Fraction(info["r_frame_rate"]):
        raise ValueError("Requires constant-rate video; verify/normalize timing separately")
    timing = probe(source)  # Check decoded PTS; equal nominal FPS alone does not prove CFR.
    x,y,w,h = roi
    if h != 16 or min(x,y) < 0 or x+w > info["width"] or y+h > info["height"]:
        raise ValueError("ROI must be inside the video, 16 pixels high")
    if not x <= low < high < x+w:
        raise ValueError("Slider window must be inside the ROI")
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(source),
                          "-vf", f"crop={w}:{h}:{x}:{y},format=gray", "-an", "-fps_mode", "passthrough",
                          "-f", "rawvideo", "pipe:1"], capture_output=True, check=True).stdout
    size = w*h
    trace = [slider_center(raw[i:i+size],w,h) for i in range(0,len(raw),size)]
    if len(trace) != timing["count"]:
        raise ValueError("Slider decoding frame count differs from the source timing audit")
    trace = [v+x if v is not None else None for v in trace]
    bounds = passage_boundaries(trace)
    candidates, rejected = [], []
    for index,(start,end) in enumerate(zip(bounds,bounds[1:]),1):
        try:
            fit = fit_passage(trace,start,end,low,high,float(fps))
            candidates.append(dict(id=f"cam{index:02d}", source_interval_frames=[start,end], **fit))
        except ValueError as error:
            rejected.append(dict(passage=index, source_interval_frames=[start,end], reason=str(error)))
    if not candidates:
        raise ValueError("No reliable candidates; inspect the slider ROI and source video")
    # Match duration by trimming only; never independently resample a view.
    count = min(c["end_frame_exclusive"]-c["first_frame"] for c in candidates)
    if count <= 0:
        raise ValueError("Empty common replay interval")
    for c in candidates:
        c["end_frame_exclusive"] = c["first_frame"]+count
    speeds = [c["pixels_per_second"] for c in candidates]
    if max(speeds)/min(speeds) > 1.02:
        raise ValueError("Replay speeds differ by >2%; no automatic batch export")
    output.mkdir(parents=True)
    report = dict(source=str(source), fps=str(fps), resolution=[info["width"],info["height"]],
                  slider_roi=roi, slider_window=[low,high], camera_motion="moving",
                  frames_per_clip=count, duration_seconds=count/float(fps),
                  candidates=candidates, rejected=rejected,
                  status="candidate cuts; visual synchronization review required", exported=False,
                  caution="Camera IDs are passage order; angles and duplicate viewpoints are unverified.")
    manifest = output / "cuts.json"
    def save():
        manifest.write_text(json.dumps(report,indent=2),encoding="utf-8")
    save()
    if execute:
        def export(c):
            # Re-encode from an accurate decoded seek; stream copy can shift to keyframes.
            target = output / (c["id"]+".mp4")
            run(["ffmpeg", "-nostdin", "-v", "error", "-n", "-ss", f"{c['first_frame']/float(fps):.9f}",
                 "-i", source, "-map", "0:v:0", "-an", "-frames:v", count,
                 "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-threads", "2",
                 "-fps_mode", "passthrough", "-movflags", "+faststart", target])
            actual = json.loads(run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                     "-show_entries", "stream=nb_read_frames", "-of", "json", target]))
            if int(actual["streams"][0]["nb_read_frames"]) != count:
                raise ValueError(f"Exported frame count differs: {target}")
            print(f"Exported {c['id']}: {count} frames",flush=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(export,candidates))
        report["exported"] = True
        save()
    print(f"{len(candidates)} candidates, {len(rejected)} rejected, {count} frames/clip. Report: {manifest}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--slider-roi",nargs=4,type=int,default=[140,1138,414,16],metavar=("X","Y","W","H"))
    p.add_argument("--slider-window",nargs=2,type=float,default=[195,525],metavar=("START_X","END_X"))
    p.add_argument("--execute",action="store_true",help="Export video clips; otherwise write proposals only")
    args=p.parse_args()
    try:
        split(args.source,args.output,args.slider_roi,*args.slider_window,args.execute)
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        p.exit(1,f"ERROR: {error}\nOriginal videos are unchanged. Any partial output is retained.\n")
