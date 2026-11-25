"""Check reserved sample8 camera using only background correspondences and held-back matches."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image
import pycolmap
import _bootstrap
from skate4d.localization import unique_correspondences
from prepare_dense_fixed_init import read_cloud
from static_board_geometry import project


def summarize(errors):
    return dict(count=len(errors),median_pixels=float(np.median(errors)),p90_pixels=float(np.percentile(errors,90))) if len(errors) else dict(count=0)


def run(source,clips,reference,hull_path,output):
    if output.exists():raise ValueError('Choose a fresh output')
    output.mkdir(parents=True)
    manifest=json.loads((source/'manifest.json').read_text())
    record=next(r for r in manifest['frames'] if r['camera_id']=='view20' and Path(r['image_path']).stem=='008')
    cut=next(r for r in json.loads((clips/'cuts.json').read_text())['candidates'] if r['id']=='view20')
    image_path=output/'query-native.png'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(clips/cut['file_path']),'-vf',f'select=eq(n\\,{record["clip_frame"]})',
        '-frames:v','1','-fps_mode','passthrough',str(image_path)],check=True)
    model_path=reference/'sparse/0'
    fingerprints={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in model_path.glob('*.bin')}
    model=pycolmap.Reconstruction(model_path)
    options=pycolmap.FeatureExtractionOptions(num_threads=4,max_image_size=2500);options.sift.max_num_features=8192
    extractor=pycolmap.FeatureExtractor.create(options,pycolmap.Device.cpu)
    matcher=pycolmap.FeatureMatcher.create(pycolmap.FeatureMatchingOptions(num_threads=4),pycolmap.Device.cpu)
    with Image.open(image_path) as image:keypoints,descriptors=extractor.extract_from_uint8_array(np.array(image.convert('L')))
    xy=np.array([[p.x,p.y] for p in keypoints])
    with Image.open(reference/'masks/view20.png.png') as image:mask=np.array(image)>0
    keep=np.array([i for i,(x,y) in enumerate(xy) if 0<=x<mask.shape[1] and 0<=y<mask.shape[0] and mask[int(y),int(x)]])
    xy=xy[keep];query=pycolmap.FeatureDescriptors(descriptors.type,descriptors.data[keep]);votes={}
    with pycolmap.Database.open(reference/'database.db') as database:
        for image in model.images.values():
            matches=matcher.match(pycolmap.FeatureKeypoints(),query,pycolmap.FeatureKeypoints(),database.read_descriptors(image.image_id))
            for q,r in matches:
                point=image.points2D[int(r)]
                if point.has_point3D():votes.setdefault(int(q),set()).add(int(point.point3D_id))
    pairs=unique_correspondences(votes)
    pixels=np.array([xy[q] for q,_ in pairs]);points=np.array([model.points3D[p].xyz for _,p in pairs])
    np.savez_compressed(output/'background-matches.npz',pixels=pixels,points=points)
    original=next(iter(model.cameras.values()))
    old=json.loads(Path('outputs/clean-replay-pipeline/holdout.json').read_text())
    pose=np.array(old['world_to_camera']);k=original.params.copy()
    baseline_errors=np.linalg.norm(project(points,pose,k)[0]-pixels,axis=1)
    # Fix a geometrically consistent support set for the diagnostic. This is conditional
    # cross-validation against the existing map, not an untouched camera-calibration test.
    support=np.where(baseline_errors<4)[0]
    order=np.random.default_rng(24).permutation(support);fit=order[:int(.7*len(order))];check=order[int(.7*len(order)):]
    hull,_=read_cloud(hull_path)
    normalization=manifest['world_normalization'];hull=hull*normalization['scale']+np.array(normalization['origin'])
    anchor=hull.mean(0);distances=np.linalg.norm(points-anchor,axis=1)
    nearby=distances<np.percentile(distances[support],25)
    report=dict(camera='view20',sample=8,clip_frame=record['clip_frame'],background_correspondences=len(pairs),
        support_count=len(support),fit_count=len(fit),check_count=len(check),
        split='Seed24 70/30 split of matches consistent within4 native pixels of the existing pose; conditional diagnostic, not independent calibration truth',
        map_sha256=fingerprints,original=dict(focal_native_pixels=float(k[0]),check=summarize(baseline_errors[check]/2),nearby=summarize(baseline_errors[support[nearby[support]]]/2)),candidates={})
    for refine in [False,True]:
        camera=pycolmap.Camera(model=original.model,width=original.width,height=original.height,params=k.copy())
        estimation=pycolmap.AbsolutePoseEstimationOptions();estimation.ransac.max_error=4;estimation.ransac.random_seed=0
        result=pycolmap.estimate_and_refine_absolute_pose(pixels[fit],points[fit],camera,estimation,
            pycolmap.AbsolutePoseRefinementOptions(refine_focal_length=refine,refine_extra_params=False))
        if result is None:raise ValueError('Diagnostic PnP failed')
        candidate=result['cam_from_world'].matrix();errors=np.linalg.norm(project(points,candidate,camera.params)[0]-pixels,axis=1)
        shift=np.linalg.norm(project(hull,candidate,camera.params)[0]-project(hull,pose,k)[0],axis=1)/2
        report['candidates']['refine_focal' if refine else 'fixed_focal']=dict(focal_native_pixels=float(camera.params[0]),
            check=summarize(errors[check]/2),nearby=summarize(errors[support[nearby[support]]]/2),
            median_hull_projection_shift_working_pixels=float(np.median(shift)),world_to_camera=candidate.tolist())
    assert fingerprints=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in model_path.glob('*.bin')}
    report['limitations']='Uses only static-background observations. Existing map/calibration may share systematic error. Nearby means closest quartile of matched background points in3D, not surveyed landmarks. No camera changes applied.'
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-clean-pilot'))
    p.add_argument('--clips',type=Path,default=Path('data/raw/true-skate-clean-2026-11-24'))
    p.add_argument('--reference',type=Path,default=Path('outputs/clean-replay-pipeline/geometry'))
    p.add_argument('--hull',type=Path,default=Path('outputs/static-board-core/strict-hull.ply'))
    p.add_argument('--output',type=Path,default=Path('outputs/reserved-camera-audit'))
    a=p.parse_args();run(a.source,a.clips,a.reference,a.hull,a.output)
