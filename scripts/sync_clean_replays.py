"""Candidate alignment from a persistent green score event in clean clips."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

import numpy as np


def sync(clips,output):
    if output.exists():raise ValueError("Choose a fresh event report")
    rows=json.loads((clips/"cuts.json").read_text())["candidates"]
    def check(row):
        raw=subprocess.check_output(["ffmpeg","-nostdin","-v","error","-i",str(clips/row["file_path"]),
            "-vf","crop=1126:1000:0:0,scale=338:300","-pix_fmt","rgb24","-f","rawvideo","pipe:1"])
        frames=np.frombuffer(raw,np.uint8).reshape(-1,300,338,3).astype(np.int16)
        assert len(frames)==row["frames"]
        green=(frames[:,:,:,1]>200)&(frames[:,:,:,1]-frames[:,:,:,0]>100)&(frames[:,:,:,1]-frames[:,:,:,2]>100)
        counts=green.sum((1,2))
        onsets=[i for i in range(len(counts)-4) if counts[i]>=5 and (counts[i:i+5]>=5).sum()>=3]
        return dict(id=row["id"],first_green_frame=onsets[0] if onsets else None,
            max_green_pixels=int(counts.max()),counts=counts.tolist())
    results=list(ThreadPoolExecutor(max_workers=3).map(check,rows))
    if any(r["first_green_frame"] is None for r in results):raise ValueError("Missing score event in a view")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(results,indent=2)+"\n")
    for record in results:print(record["id"],"score frame",record["first_green_frame"],flush=True)
    print("UI-event candidate alignment only; verify action and score labels before training.",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clips",type=Path,default=Path("data/raw/true-skate-clean-2026-11-24"))
    parser.add_argument("--output",type=Path,default=Path("outputs/clean-replay-pipeline/green-events.json"))
    args=parser.parse_args();sync(args.clips,args.output)
