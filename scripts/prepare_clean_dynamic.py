"""Prepare the new menu-hidden replay around a shared score event."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image,ImageDraw
import pycolmap
from prepare_dense_fixed_init import write_cloud


def prepare(clips,reference,events_path,holdout_path,output):
    if output.exists():raise ValueError("Choose a fresh output")
    geometry=json.loads((reference/"report.json").read_text())
    held=json.loads(holdout_path.read_text())
    if not held["accepted"]:raise ValueError("Holdout localization failed")
    model_path=reference/"sparse"/str(geometry["selected_model"])
    assert held["map_sha256"]=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in model_path.glob("*.bin")}
    model=pycolmap.Reconstruction(model_path)
    camera=next(iter(model.cameras.values()))
    events={r["id"]:r for r in json.loads(events_path.read_text())}
    cuts=json.loads((clips/"cuts.json").read_text())
    rows=cuts["candidates"]
    lookup={r["id"]:r for r in rows}
    holdout=geometry["heldout_view"]
    training=[im.name.removesuffix(".png") for im in model.images.values() if im.has_pose]
    training=sorted(training)
    assert holdout not in training and "view05" not in training and "view18" not in training
    poses={im.name.removesuffix(".png"):im.cam_from_world().matrix().copy() for im in model.images.values() if im.has_pose}
    poses[holdout]=np.array(held["world_to_camera"])
    indices_relative=list(range(-60,-23,3))
    output.mkdir(parents=True)
    records=[]
    diagnostic=[]
    event_sheet=Image.new("RGB",(4*300,((len(rows)+3)//4)*210),"white");event_draw=ImageDraw.Draw(event_sheet)
    for row,name in enumerate(training+[holdout]):
        onset=events[name]["first_green_frame"]
        if onset is None:raise ValueError(f"No alignment event in {name}")
        indices=[onset+i for i in indices_relative]
        assert min(indices)>=0 and max(indices)<lookup[name]["frames"]
        select="+".join(f"eq(n\\,{i})" for i in indices)
        raw=subprocess.check_output(["ffmpeg","-nostdin","-v","error","-hwaccel","cuda","-i",str(clips/lookup[name]["file_path"]),
            "-vf",f"select={select},scale=563:1218","-frames:v",str(len(indices)),"-fps_mode","passthrough",
            "-pix_fmt","rgb24","-f","rawvideo","pipe:1"])
        size=563*1218*3
        assert len(raw)==size*len(indices)
        (output/"images"/name).mkdir(parents=True)
        sheet=Image.new("RGB",(900,456),"white");draw=ImageDraw.Draw(sheet)
        for j,index in enumerate(indices):
            image=Image.frombytes("RGB",(563,1218),raw[j*size:(j+1)*size])
            path=f"images/{name}/{j:03d}.png"
            image.save(output/path,compress_level=3)
            records.append(dict(camera_id=name,image_path=path,time=j/12,clip_frame=index,
                seconds_relative_to_score=indices_relative[j]/60,split="test" if name==holdout else "train",
                world_to_camera=poses[name].tolist()))
            if j in [0,6,12]:
                col=[0,6,12].index(j)
                sheet.paste(image.crop((0,400,563,1200)).resize((300,426)),(col*300,30))
                draw.text((col*300+5,8),f"{name} | event {indices_relative[j]/60:+.2f}s | frame {index}",fill="black")
        diagnostic.append(sheet)
        roi=subprocess.check_output(["ffmpeg","-nostdin","-v","error","-ss",str((onset+4)/60),"-i",str(clips/lookup[name]["file_path"]),
            "-vf","crop=1126:650:0:300,scale=300:173","-frames:v","1","-pix_fmt","rgb24","-f","rawvideo","pipe:1"])
        event_sheet.paste(Image.frombytes("RGB",(300,173),roi),((row%4)*300,(row//4)*210+30))
        event_draw.text(((row%4)*300+5,(row//4)*210+7),name+" / detected score",fill="black")
    selected=[p for p in model.points3D.values() if p.track.length()>=3 and p.error<=2]
    points=np.array([p.xyz for p in selected],dtype=np.float64)
    colors=np.array([p.color for p in selected],dtype=np.uint8)
    centers=np.array([-poses[name][:,:3].T@poses[name][:,3] for name in training])
    origin=centers.mean(0);scale=float(np.linalg.norm(centers-origin,axis=1).max())
    points=(points-origin)/scale
    for record in records:
        pose=np.array(record["world_to_camera"])
        pose[:,3]=(pose[:,:3]@origin+pose[:,3])/scale
        record["world_to_camera"]=pose.tolist()
    write_cloud(output/"points3D_multipleview.ply",points.astype(np.float32),colors)
    (output/"background").mkdir()
    with Image.open(clips/"background/reference-for-view19.png") as image:image.resize((563,1218)).save(output/"background/view19.png")
    for first in range(0,len(diagnostic),3):
        page=Image.new("RGB",(900,456*len(diagnostic[first:first+3])),"white")
        for j,image in enumerate(diagnostic[first:first+3]):page.paste(image,(0,456*j))
        page.save(output/f"sync-review-{first//3}.jpg",quality=92)
    event_sheet.save(output/"score-event-review.jpg",quality=94)
    focal=float(camera.params[0])/2
    report=dict(training_cameras=training,heldout_camera=holdout,evaluation_training_camera="view19",frames=records,
        image_resolution=[563,1218],intrinsics=[focal,281.5,609.0],crop_xywh=[0,0,1126,2436],
        source_fps=60,sample_fps=20,physical_time_span_seconds=.6,
        normalized_time_rule="sample index / 12; 0.6 seconds, from -1.0 to -0.4 seconds before the detected score event",
        event_onsets_frames={name:events[name]["first_green_frame"] for name in training+[holdout]},
        initialization_points=len(points),initialization="Observed training-background sparse points with >=3 tracks and error <=2 pixels; no interpolation or board-specific seeds",
        world_normalization=dict(origin=origin.tolist(),scale=scale),
        background_reference="background/view19.png from empty view18, for diagnostics; no foreground loss weighting",
        source_sha256=cuts["source_sha256"],limitations="One UI event alignment, not proven frame-perfect sync. Shared estimated intrinsics. New capture/preparation differs from earlier pilots, not a data-only ablation.")
    (output/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!='frames'},indent=2),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--clips",type=Path,default=Path("data/raw/true-skate-clean-2026-11-24"))
    p.add_argument("--reference",type=Path,default=Path("outputs/clean-replay-pipeline/geometry"))
    p.add_argument("--events",type=Path,default=Path("outputs/clean-replay-pipeline/green-events.json"))
    p.add_argument("--holdout",type=Path,default=Path("outputs/clean-replay-pipeline/holdout.json"))
    p.add_argument("--output",type=Path,default=Path("data/processed/true-skate-clean-pilot"))
    a=p.parse_args();prepare(a.clips,a.reference,a.events,a.holdout,a.output)
