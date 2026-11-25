"""Reference-derived foreground diagnostic for view19, not semantic ground truth."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw


def evaluate(source,run,output,checkpoints):
    with Image.open(source/"background/view19.png") as image:background=np.array(image.convert("RGB"),dtype=np.float32)/255
    targets=[]
    for i in range(13):
        with Image.open(source/f"images/view19/{i:03d}.png") as image:targets.append(np.array(image.convert("RGB"),dtype=np.float32)/255)
    targets=np.stack(targets)
    changing=np.ptp(targets,axis=0).max(2)>45/255
    masks=(np.abs(targets-background).max(3)>40/255)&changing[None]
    if any(mask.sum()<20 for mask in masks):raise ValueError("Foreground diagnostic region too small")
    def measure(predictions):
        mse=[float(((pred-target)**2)[mask].mean()) for pred,target,mask in zip(predictions,targets,masks)]
        return dict(mean_psnr_db=float(np.mean([-10*np.log10(max(value,1e-12)) for value in mse])),
            mean_absolute_error=float(np.mean([np.abs(pred-target)[mask].mean() for pred,target,mask in zip(predictions,targets,masks)])))
    results={"background_plate_baseline":measure(np.repeat(background[None],13,0)),"checkpoints":{}}
    for iteration in checkpoints:
        metrics={}
        for kind in ["renders","frozen-time"]:
            images=[]
            for i in range(13):
                with Image.open(run/f"renders-{iteration}/train-view19/{kind}/{i:03d}.png") as image:images.append(np.array(image.convert("RGB"),dtype=np.float32)/255)
            metrics[kind]=measure(images)
        results["checkpoints"][str(iteration)]=metrics
    manifest=json.loads((source/"manifest.json").read_text())
    used=bool(manifest.get("foreground_loss"))
    results.update(mask_pixels_per_frame=[int(mask.sum()) for mask in masks],
        method="abs RGB target-empty-background max>40/255 AND target temporal range>45/255, view19 only; per-frame mask",
        masks_used_in_training=used,
        caution="Reference-derived candidate foreground, may include shadows/appearance effects. Not semantic labels or independent object geometry validation. "+("Masks used for training: these are training-fit metrics, not independent foreground validation." if used else "Masks not used in this training."))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(results,indent=2)+"\n")
    sheet=Image.new("RGB",(900,1368),"white");draw=ImageDraw.Draw(sheet)
    for row,index in enumerate([0,6,12]):
        target=(targets[index]*255).round().astype(np.uint8)
        overlay=target.copy()
        overlay[masks[index]]=(overlay[masks[index]]*.4+[0,150,0]).clip(0,255).astype(np.uint8)
        binary=np.repeat((masks[index]*255).astype(np.uint8)[:,:,None],3,2)
        for column,(label,array) in enumerate([("Recording",target),("Reference-derived foreground",overlay),("Candidate foreground pixels",binary)]):
            image=Image.fromarray(array).crop((0,400,563,1200)).resize((300,426))
            sheet.paste(image,(column*300,row*456+30))
            draw.text((column*300+5,row*456+8),f"f{index} / {label}",fill="black")
    sheet.save(output.parent/"foreground-reference-comparison.jpg",quality=92)
    print(json.dumps(results,indent=2),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,default=Path("data/processed/true-skate-clean-pilot"))
    p.add_argument("--run",type=Path,default=Path("outputs/clean-replay-pipeline/gpu"))
    p.add_argument("--output",type=Path,default=Path("outputs/clean-replay-pipeline/foreground-evaluation.json"))
    p.add_argument("--checkpoints",type=int,nargs="+",default=[2000,5000])
    a=p.parse_args();evaluate(a.source,a.run,a.output,a.checkpoints)
