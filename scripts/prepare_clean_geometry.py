"""New capture: training-only static-background SfM from temporal medians."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image,ImageFilter
import pycolmap


def run(clips,output):
    if output.exists():raise ValueError("Choose a fresh output")
    cuts=json.loads((clips/"cuts.json").read_text())
    rows=cuts["candidates"]
    holdout="view20"
    training=[r["id"] for r in rows if r["id"]!=holdout]
    output.mkdir(parents=True)
    for name in ["images","masks"]:(output/name).mkdir()
    def prepare(row):
        name=row["id"]
        indices=np.linspace(3,row["frames"]-4,5).round().astype(int)
        select="+".join(f"eq(n\\,{i})" for i in indices)
        raw=subprocess.check_output(["ffmpeg","-nostdin","-v","error","-hwaccel","cuda","-i",str(clips/row["file_path"]),
            "-vf",f"select={select}","-frames:v","5","-fps_mode","passthrough","-pix_fmt","rgb24","-f","rawvideo","pipe:1"])
        frames=np.frombuffer(raw,np.uint8).reshape(5,2436,1126,3)
        background=np.median(frames,axis=0).astype(np.uint8)
        variation=frames.max(0).astype(np.int16)-frames.min(0).astype(np.int16)
        moving=(variation.max(2)>25).astype(np.uint8)*255
        if name=="view19":
            with Image.open(clips/"background/reference-for-view19.png") as image:background=np.array(image.convert("RGB"))
        mask=Image.fromarray(moving).filter(ImageFilter.MaxFilter(7))
        mask=Image.fromarray(255-np.array(mask))
        Image.fromarray(background).save(output/"images"/(name+".png"),compress_level=3)
        mask.save(output/"masks"/(name+".png.png"))
        return dict(id=name,source_frames=indices.tolist(),excluded_changing_fraction=float(np.mean(np.array(mask)==0)),
            background="view18 empty reference" if name=="view19" else "five-frame temporal median")
    preparations=list(ThreadPoolExecutor(max_workers=2).map(prepare,rows))
    print("Background images prepared; holdout excluded:",holdout,flush=True)
    database=output/"database.db"
    reader=pycolmap.ImageReaderOptions(camera_model="SIMPLE_PINHOLE",camera_params="1200,563,1218",mask_path=output/"masks")
    extraction=pycolmap.FeatureExtractionOptions(num_threads=4,max_image_size=2500)
    extraction.sift.max_num_features=8192
    start=time.monotonic()
    pycolmap.extract_features(database,output/"images",image_names=[n+".png" for n in training],
        camera_mode=pycolmap.CameraMode.SINGLE,reader_options=reader,extraction_options=extraction,device=pycolmap.Device.cpu)
    pycolmap.match_exhaustive(database,matching_options=pycolmap.FeatureMatchingOptions(num_threads=4),device=pycolmap.Device.cpu)
    options=pycolmap.IncrementalPipelineOptions(num_threads=4,random_seed=0,max_num_models=3,min_model_size=4,
        max_runtime_seconds=180,ba_refine_principal_point=False)
    models=pycolmap.incremental_mapping(database,output/"images",output/"sparse",options=options)
    summaries=[]
    for key,model in models.items():
        names=sorted(im.name for im in model.images.values() if im.has_pose)
        assert holdout+".png" not in names
        summaries.append(dict(model_id=key,images=names,registered=len(names),points=model.num_points3D(),
            mean_error=model.compute_mean_reprojection_error(),focal=float(next(iter(model.cameras.values())).params[0])))
    plausible=[s for s in summaries if 300<s["focal"]<3000]
    if not plausible:raise ValueError("No plausible shared-focal reconstruction")
    selected=max(plausible,key=lambda s:s["registered"])
    report=dict(source_sha256=cuts["source_sha256"],training_views=training,heldout_view=holdout,
        image_size=[1126,2436],models=summaries,selected_model=selected["model_id"],preparations=preparations,
        elapsed_geometry_seconds=time.monotonic()-start,method="Full-resolution background medians and temporal-change masks; shared SIMPLE_PINHOLE with fixed image-center principal point; training views only",
        caution="Sparse geometry, not dense stereo. Masks are temporal diagnostics, not semantic segmentation. Focal plausibility filtering does not independently validate calibration.")
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!='preparations'},indent=2),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--clips",type=Path,default=Path("data/raw/true-skate-clean-2026-11-24"))
    p.add_argument("--output",type=Path,default=Path("outputs/clean-replay-pipeline/geometry"))
    a=p.parse_args();run(a.clips,a.output)
