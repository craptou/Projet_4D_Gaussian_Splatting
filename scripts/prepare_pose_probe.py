"""Prepare a small masked moving-camera SfM pilot from the original recording."""
import argparse
import json
from pathlib import Path
import subprocess
from fractions import Fraction
from PIL import Image, ImageDraw
import _bootstrap
from skate4d.dataset import ROOT


def build(config_path, output):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cuts = json.loads((ROOT/config["cuts"]).read_text(encoding="utf-8"))
    if output.exists():
        raise ValueError("Output exists; use a new destination")
    if config["reserved_holdout"] in config["training_passages"]:
        raise ValueError("Held-out passage must not be in training")
    indices = config["sample_indices_zero_based"]
    if not indices or sorted(set(indices)) != indices or indices[0] < 0 or indices[-1] >= cuts["frames_per_clip"]:
        raise ValueError("Invalid sampled frame indices")
    x,y,w,h = config["crop_xywh"]
    sw,sh = cuts["resolution"]
    if min(x,y) < 0 or min(w,h) <= 0 or x+w > sw or y+h > sh:
        raise ValueError("Crop outside original image")
    output.mkdir(parents=True)
    (output/"images").mkdir()
    mask=Image.new("L",(w,h),255)
    draw=ImageDraw.Draw(mask)
    for left,top,right,bottom in config["mask_rectangles_original_xyxy"]:
        draw.rectangle((left-x,top-y,right-x-1,bottom-y-1),fill=0)
    mask.save(output/"background-mask.png")
    candidates={c["id"]:c for c in cuts["candidates"]}
    records=[]
    cols=len(indices)
    sheet=Image.new("RGB",(180*cols,275*len(config["training_passages"])),"white")
    preview=Image.new("RGB",sheet.size,"white")
    select="+".join(f"eq(n\\,{i})" for i in indices)
    fps=float(Fraction(cuts["fps"]))
    for row,name in enumerate(config["training_passages"]):
        candidate=candidates[name]
        cmd=["ffmpeg","-nostdin","-v","error","-ss",f"{candidate['first_frame']/fps:.9f}",
             "-i",str(ROOT/config["source"]),"-vf",f"select={select},crop={w}:{h}:{x}:{y}",
             "-frames:v",str(len(indices)),"-fps_mode","passthrough","-an","-pix_fmt","rgb24","-f","rawvideo","pipe:1"]
        result=subprocess.run(cmd,capture_output=True,check=True)
        size=w*h*3
        if len(result.stdout)!=size*len(indices):
            raise ValueError(f"Unexpected decoded frame count for {name}")
        (output/"images"/name).mkdir()
        for col,index in enumerate(indices):
            im=Image.frombytes("RGB",(w,h),result.stdout[col*size:(col+1)*size])
            rel=Path(name)/f"frame_{index+1:05d}.png"
            im.save(output/"images"/rel)
            records.append(dict(image_path=rel.as_posix(),camera_id=name,clip_frame_index=index,
                source_frame_index=candidate["first_frame"]+index,time_seconds=index/fps,split="train"))
            masked=Image.composite(im,Image.new("RGB",im.size,"black"),mask)
            for image,target in ((im,sheet),(masked,preview)):
                image.thumbnail((180,249))
                target.paste(image,(col*180,row*275+23))
                ImageDraw.Draw(target).text((col*180+3,row*275+3),f"{name} / f{index+1}",fill="black")
    sheet.save(output/"contact-sheet.jpg")
    preview.save(output/"masked-contact-sheet.jpg")
    manifest=dict(config=config,frames=records,cropped_resolution=[w,h],fps=cuts["fps"],
        coordinate_change="K_crop = [[fx,0,cx-x],[0,fy,cy-y],[0,0,1]]; no resize",
        status="pilot only: approximate synchronization, uncalibrated per-frame cameras")
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Prepared {len(records)} images and background mask in {output}")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",type=Path,default=ROOT/"configs/datasets/replay-pose-probe.json")
    p.add_argument("--output",type=Path,default=ROOT/"data/processed/replay-pose-probe")
    args=p.parse_args()
    try:
        build(args.config,args.output)
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as error:
        p.exit(1,f"ERROR: {error}\nPartial outputs retained; source recordings unchanged.\n")
