"""Measure temporal variation in target-stable and target-changing regions.

Masks are pixel-variation diagnostics, not skateboard segmentation.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def analyze(renders,output):
    if output.exists():raise ValueError("Output exists; choose a fresh report path")
    results={}
    for group in ["test-cam13","train-cam08"]:
        stacks={}
        for kind in ["gt","renders","frozen-time"]:
            arrays=[]
            for index in range(13):
                with Image.open(renders/group/kind/f"{index:03d}.png") as image:
                    arrays.append(np.array(image.convert("RGB"),dtype=np.float32)/255)
            stacks[kind]=np.stack(arrays)
        if len({value.shape for value in stacks.values()})!=1:
            raise ValueError("Target/render dimensions differ")
        variation=np.ptp(stacks["gt"],axis=0).max(-1)
        stable=variation<=8/255
        change=variation>45/255
        if not stable.any() or not change.any():
            raise ValueError("Both diagnostic regions must contain pixels")
        record=dict(stable_target_region_pixels=int(stable.sum()),
            stable_target_region_fraction=float(stable.mean()),
            moving_target_region_pixels=int(change.sum()),interframe_mae_255={})
        for kind,value in stacks.items():
            difference=np.abs(value[1:]-value[:-1])
            record["interframe_mae_255"][kind]=dict(whole_image=float(difference.mean()*255),
                stable_target_region=float(difference[:,stable,:].mean()*255),
                changing_target_region=float(difference[:,change,:].mean()*255))
        results[group]=record
    report=dict(method="13 decoded RGB PNGs; stable-target mask: per-pixel max-channel range <=8/255 over time. Change mask >45/255. MAE of consecutive frames, in 0-255 RGB intensity units. Masks derived from targets, not semantic segmentation.",cameras=results)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renders",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    analyze(args.renders,args.output)
