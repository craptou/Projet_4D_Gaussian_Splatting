"""Background-only sensitivity check: separate focal length per training view."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import pycolmap


def run(reference,output):
    if output.exists():raise ValueError('Choose a fresh output')
    output.mkdir(parents=True)
    original=reference/'database.db'
    original_hash=hashlib.sha256(original.read_bytes()).hexdigest()
    shutil.copytree(reference/'images',output/'images')
    shutil.copytree(reference/'masks',output/'masks')
    names=json.loads((reference/'report.json').read_text())['training_views']
    reader=pycolmap.ImageReaderOptions(camera_model='SIMPLE_PINHOLE',camera_params='1200,563,1218',mask_path=output/'masks')
    extraction=pycolmap.FeatureExtractionOptions(num_threads=4,max_image_size=2500)
    extraction.sift.max_num_features=8192
    pycolmap.extract_features(output/'database.db',output/'images',image_names=[n+'.png' for n in names],
        camera_mode=pycolmap.CameraMode.PER_IMAGE,reader_options=reader,extraction_options=extraction,device=pycolmap.Device.cpu)
    pycolmap.match_exhaustive(output/'database.db',matching_options=pycolmap.FeatureMatchingOptions(num_threads=4),device=pycolmap.Device.cpu)
    options=pycolmap.IncrementalPipelineOptions(num_threads=4,random_seed=0,max_num_models=3,min_model_size=4,
        max_runtime_seconds=180,ba_refine_principal_point=False)
    models=pycolmap.incremental_mapping(output/'database.db',output/'images',output/'sparse',options=options)
    rows=[]
    for key,model in models.items():
        rows.append(dict(model_id=key,registered=model.num_reg_images(),points=model.num_points3D(),
            mean_error=model.compute_mean_reprojection_error(),focals={im.name:float(model.camera(im.camera_id).params[0]) for im in model.images.values() if im.has_pose}))
    report=dict(models=rows,method='Same background images/masks and extraction settings, separate SIMPLE_PINHOLE focal per image; principal point fixed; training views only',
        heldout_used=False,original_database_unchanged=hashlib.sha256(original.read_bytes()).hexdigest()==original_hash,
        caveat='Sensitivity analysis, not independent calibration ground truth. More parameters may overfit.')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,default=Path('outputs/clean-replay-pipeline/geometry'))
    p.add_argument('--output',type=Path,default=Path('outputs/static-independent-focals'))
    a=p.parse_args();run(a.reference,a.output)
