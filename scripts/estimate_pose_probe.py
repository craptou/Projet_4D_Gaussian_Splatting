"""Bounded CPU sparse SfM pilot with an explicit static-background feature mask."""
import argparse
import json
import time
from pathlib import Path
import numpy as np
import pycolmap
import _bootstrap
from skate4d.dataset import ROOT


def estimate(dataset, output, max_seconds):
    if max_seconds <= 0:
        raise ValueError("Mapping time budget must be positive")
    if output.exists():
        raise ValueError("Output exists; use a new destination")
    meta=json.loads((dataset/"manifest.json").read_text(encoding="utf-8"))
    frames=meta["frames"]
    if any(f["camera_id"]==meta["config"]["reserved_holdout"] for f in frames):
        raise ValueError("Holdout leaked into SfM images")
    output.mkdir(parents=True)
    db=output/"database.db"
    start=time.monotonic()
    w,h=meta["cropped_resolution"]
    x,y,_,_=meta["config"]["crop_xywh"]
    # Original render area is horizontally centered, with black side bars.
    # This is an initialization/assumption, not a measured camera calibration.
    source_width,source_height=json.loads((ROOT/meta["config"]["cuts"]).read_text(encoding="utf-8"))["resolution"]
    cx,cy=source_width/2-x,source_height/2-y
    initial_focal=1.2*max(w,h)
    reader=pycolmap.ImageReaderOptions(camera_model="SIMPLE_PINHOLE",
        camera_params=f"{initial_focal},{cx},{cy}",camera_mask_path=dataset/"background-mask.png")
    extraction=pycolmap.FeatureExtractionOptions(num_threads=4,max_image_size=1000)
    extraction.sift.max_num_features=2048
    print("PHASE extraction",flush=True)
    pycolmap.extract_features(db,dataset/"images",image_names=[f["image_path"] for f in frames],
        camera_mode=pycolmap.CameraMode.SINGLE,reader_options=reader,
        extraction_options=extraction,device=pycolmap.Device.cpu)
    print("PHASE matching",flush=True)
    matching=pycolmap.FeatureMatchingOptions(num_threads=4)
    pycolmap.match_exhaustive(db,matching_options=matching,device=pycolmap.Device.cpu)
    print("PHASE mapping",flush=True)
    options=pycolmap.IncrementalPipelineOptions(num_threads=4,random_seed=0,
        max_num_models=3,min_model_size=4,max_runtime_seconds=max_seconds,
        ba_refine_principal_point=False)
    models=pycolmap.incremental_mapping(db,dataset/"images",output/"sparse",options=options)
    summaries=[]
    provenance={f["image_path"]:f for f in frames}
    for key,model in models.items():
        model.export_PLY(output/f"model-{key}.ply")
        records=[]
        for image in model.images.values():
            if not image.has_pose:
                continue
            pose=image.cam_from_world()
            records.append(dict(**provenance[image.name],world_to_camera=pose.matrix().tolist(),
                center_world=image.projection_center().tolist(),intrinsics_id=int(image.camera_id)))
        cameras={str(k):dict(model=str(cam.model_name),width=int(cam.width),height=int(cam.height),
                            params=cam.params.tolist()) for k,cam in model.cameras.items()}
        (output/f"poses-model-{key}.json").write_text(json.dumps(dict(cameras=cameras,images=records),indent=2),encoding="utf-8")
        summaries.append(dict(model_id=key,registered_images=model.num_reg_images(),
            points3D=model.num_points3D(),mean_reprojection_error=model.compute_mean_reprojection_error(),
            mean_track_length=model.compute_mean_track_length(),
            registered_by_passage={name:sum(r["image_path"].startswith(name+"/") for r in records)
                for name in meta["config"]["training_passages"]}))
    result=dict(pycolmap_version=pycolmap.__version__,cuda_available=pycolmap.has_cuda,
        device="CPU",image_count=len(frames),models=summaries,elapsed_seconds=time.monotonic()-start,
        intrinsics_assumption="Shared fixed SIMPLE_PINHOLE, centered original 720x1280 render; crop principal point adjusted, focal optimized from heuristic initialization.",
        initial_focal_pixels=initial_focal,principal_point_crop=[cx,cy],
        status="pilot sparse geometry; not a validated moving-camera dataset or 4DGS reproduction",
        configuration=dict(extraction=extraction.todict(),matching=matching.todict(),mapping=options.todict()))
    # Pybind options include enums/sets/path objects; serialize their readable representations.
    (output/"report.json").write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")
    print(json.dumps(dict(models=summaries,elapsed_seconds=result["elapsed_seconds"]),indent=2),flush=True)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",type=Path,default=ROOT/"data/processed/replay-pose-pilot")
    p.add_argument("--output",type=Path,default=ROOT/"outputs/replay-pose-pilot")
    p.add_argument("--max-mapping-seconds",type=int,default=180)
    args=p.parse_args()
    try:
        estimate(args.dataset,args.output,args.max_mapping_seconds)
    except (ValueError,OSError,RuntimeError) as error:
        p.exit(1,f"ERROR: {error}\nPartial database/models retained for inspection.\n")
