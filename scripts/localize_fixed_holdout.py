"""Localize cam13 using only the frozen training-background map."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pycolmap
import _bootstrap
from skate4d.localization import accepted, pose_quality, unique_correspondences


def localize(reference, output, query_id="cam13", model_id=1, mask_path=None):
    if output.exists():
        raise ValueError("Output exists")
    model_path=reference/"sparse"/str(model_id)
    files = sorted(model_path.glob("*.bin"))
    fingerprints = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    model = pycolmap.Reconstruction(model_path)
    assert all(image.name != query_id+".png" for image in model.images.values())
    native_height=next(iter(model.cameras.values())).height
    options = pycolmap.FeatureExtractionOptions(num_threads=4, max_image_size=2500 if native_height>1700 else 1700)
    options.sift.max_num_features = 8192 if native_height>1700 else 4096
    extractor = pycolmap.FeatureExtractor.create(options, pycolmap.Device.cpu)
    matcher = pycolmap.FeatureMatcher.create(pycolmap.FeatureMatchingOptions(num_threads=4), pycolmap.Device.cpu)
    with Image.open(reference/"images"/(query_id+".png")) as image:
        keypoints, descriptors = extractor.extract_from_uint8_array(np.asarray(image.convert("L")))
    xy = np.array([[p.x,p.y] for p in keypoints])
    mask = np.asarray(Image.open(mask_path or reference/"background-mask.png"))
    keep = np.array([i for i,(x,y) in enumerate(xy) if 0 <= x < mask.shape[1] and 0 <= y < mask.shape[0] and mask[int(y),int(x)] > 0])
    xy = xy[keep]
    query = pycolmap.FeatureDescriptors(descriptors.type, descriptors.data[keep])
    votes = {}
    with pycolmap.Database.open(reference/"database.db") as database:
        for image in model.images.values():
            matches = matcher.match(pycolmap.FeatureKeypoints(), query, pycolmap.FeatureKeypoints(), database.read_descriptors(image.image_id))
            for q,r in matches:
                point = image.points2D[int(r)]
                if point.has_point3D():
                    votes.setdefault(int(q),set()).add(int(point.point3D_id))
    pairs = unique_correspondences(votes)
    if len(pairs) < 30:
        raise ValueError("Insufficient 2D-3D correspondences")
    pixels = np.array([xy[q] for q,_ in pairs])
    points = np.array([model.points3D[p].xyz for _,p in pairs])
    camera = next(iter(model.cameras.values()))
    estimation = pycolmap.AbsolutePoseEstimationOptions()
    estimation.ransac.max_error = 4
    estimation.ransac.random_seed = 0
    result = pycolmap.estimate_and_refine_absolute_pose(pixels, points, camera, estimation,
        pycolmap.AbsolutePoseRefinementOptions(refine_focal_length=False, refine_extra_params=False))
    if result is None:
        raise ValueError("PnP failed")
    matrix = result["cam_from_world"].matrix()
    quality = pose_quality(pixels, points, matrix, result["inlier_mask"], camera.params)
    report = dict(camera_id=query_id, world_to_camera=matrix.tolist(), intrinsics=camera.params.tolist(),
        quality=quality, accepted=accepted(quality), map_sha256=fingerprints,
        split="Query pixels used only for localization against frozen training map, not map/4D optimization",
        limitations="Shared estimated intrinsics; no independent ground-truth camera calibration. Viewpoint independence needs separate review.")
    assert fingerprints == {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2), flush=True)
    if not report["accepted"]:
        raise ValueError("Holdout pose failed quality gate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=Path("outputs/fixed-geometry-2026-11-24"))
    parser.add_argument("--output", type=Path, default=Path("outputs/fixed-dynamic-preparation/holdout.json"))
    parser.add_argument("--query-id",default="cam13")
    parser.add_argument("--model-id",type=int,default=1)
    parser.add_argument("--mask",type=Path)
    args = parser.parse_args()
    localize(args.reference, args.output,args.query_id,args.model_id,args.mask)
