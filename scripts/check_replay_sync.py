"""Measure the appearance of the green trick-score event in the supplied capture.

This verifies a replay event, not all simulation states; it never changes cuts.
"""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
import _bootstrap
from skate4d.dataset import ROOT


def check(directory, output):
    if output.exists():
        raise ValueError("Output already exists")
    results=[]
    for video in sorted(directory.glob("cam*.mp4")):
        raw=subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(video),
            "-vf","crop=592:240:64:160","-an","-pix_fmt","rgb24","-f","rawvideo","pipe:1"],
            capture_output=True,check=True).stdout
        a=np.frombuffer(raw,dtype=np.uint8).reshape(-1,240,592,3).astype(np.int16)
        green=(a[:,:,:,1]>200)&(a[:,:,:,1]-a[:,:,:,0]>100)&(a[:,:,:,1]-a[:,:,:,2]>100)
        count=green.sum(axis=(1,2))
        # Require a persistent event; reject isolated bright green background pixels.
        detected=[i for i in range(len(count)-2) if all(count[i:i+3]>=10)]
        onset=detected[0] if detected else None
        results.append(dict(camera_id=video.stem,first_score_frame_zero_based=onset,
                            max_green_pixels=int(count.max()),pixel_counts=count.tolist()))
        print(video.stem,onset,flush=True)
    onsets=[r["first_score_frame_zero_based"] for r in results if r["first_score_frame_zero_based"] is not None]
    report=dict(roi_xywh=[64,160,592,240],method="Persistent bright-green score overlay onset, 3 frames >=10 pixels",
        source_fps=30,cameras=results,detected_count=len(onsets),total_count=len(results),
        onset_spread_frames=max(onsets)-min(onsets) if onsets else None,
        caution="One UI event only. No exact simulation synchronization claim. No clips changed.")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(f"Event detected in {len(onsets)}/{len(results)} views; spread {report['onset_spread_frames']} frames")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,default=ROOT/"data/raw/replay_auto")
    p.add_argument("--output",type=Path,default=ROOT/"outputs/capture-inspection/score-sync-check.json")
    args=p.parse_args()
    try:
        check(args.input,args.output)
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        p.exit(1,f"ERROR: {error}\n")
