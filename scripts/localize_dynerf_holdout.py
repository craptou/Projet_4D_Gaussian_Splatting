"""Check the existing SIFT/PnP localization method against supplied cam00 calibration.

Only frame 0 is used. Calibration is a reference estimate, not ground truth.
This diagnostic does not feed its estimated pose to dynamic training/evaluation.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import pycolmap
from PIL import Image

import _bootstrap
from skate4d.localization import unique_correspondences, pose_quality


def localize(scene, reference, output):
    model = pycolmap.Reconstruction(reference / "sparse")
    assert all(image.name != "cam00.png" for image in model.images.values())
    output.mkdir(parents=True, exist_ok=True)
    query_path = output / "cam00-frame0.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-threads", "2", "-i", str(scene / "cam00.mp4"),
                    "-frames:v", "1", "-vf", "scale=1352:1014", str(query_path)], check=True)
    options = pycolmap.FeatureExtractionOptions(num_threads=4, max_image_size=1352)
    options.sift.max_num_features = 4096
    extractor = pycolmap.FeatureExtractor.create(options, pycolmap.Device.cpu)
    matcher = pycolmap.FeatureMatcher.create(pycolmap.FeatureMatchingOptions(num_threads=4), pycolmap.Device.cpu)
    with Image.open(query_path) as im:
        keypoints, descriptors = extractor.extract_from_uint8_array(np.asarray(im.convert("L")))
    xy = np.array([[p.x, p.y] for p in keypoints])
    votes = {}
    with pycolmap.Database.open(reference / "database.db") as db:
        for image in model.images.values():
            matches = matcher.match(pycolmap.FeatureKeypoints(), descriptors,
                pycolmap.FeatureKeypoints(), db.read_descriptors(image.image_id))
            for q, r in matches:
                point = image.points2D[int(r)]
                if point.has_point3D():
                    votes.setdefault(int(q), set()).add(int(point.point3D_id))
    pairs = unique_correspondences(votes)
    if len(pairs) < 30:
        raise ValueError("Insufficient 2D-3D matches")
    pixels = np.array([xy[q] for q, _ in pairs])
    points = np.array([model.points3D[p].xyz for _, p in pairs])
    camera = next(iter(model.cameras.values()))
    estimation = pycolmap.AbsolutePoseEstimationOptions()
    estimation.ransac.max_error = 4
    estimation.ransac.random_seed = 0
    result = pycolmap.estimate_and_refine_absolute_pose(pixels, points, camera, estimation,
        pycolmap.AbsolutePoseRefinementOptions(refine_focal_length=False, refine_extra_params=False))
    if result is None:
        raise ValueError("PnP did not find a pose")
    estimated = result["cam_from_world"].matrix()
    # Supplied cam00 calibration is read only AFTER matching and pose estimation.
    pose = np.load(scene / "poses_bounds.npy", allow_pickle=False)[0, :15].reshape(3, 5)
    reference_rotation = np.column_stack([pose[:, 1], pose[:, 0], -pose[:, 2]]).T
    center = -estimated[:, :3].T @ estimated[:, 3]
    angle = np.degrees(np.arccos(np.clip((np.trace(estimated[:, :3] @ reference_rotation.T)-1)/2, -1, 1)))
    baseline = np.median([np.linalg.norm(image.projection_center()-pose[:, 3]) for image in model.images.values()])
    error = np.linalg.norm(center-pose[:, 3])
    report = dict(query="cam00/frame0", method="SIFT + frozen-map PnP/RANSAC; shared existing helpers",
        quality=pose_quality(pixels, points, estimated, result["inlier_mask"], camera.params),
        rotation_difference_degrees=float(angle), center_difference_scene_units=float(error),
        center_difference_over_median_camera_baseline=float(error/baseline),
        estimated_world_to_camera=estimated.tolist(),
        limitations="Single scene/frame; supplied calibration is estimated, not ground truth; no independent training of the calibration rig",
        split="cam00 pixels used only for this localization diagnostic, not map construction or dynamic optimization")
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, default=Path("data/sample/dynerf/cut_roasted_beef"))
    parser.add_argument("--reference", type=Path, default=Path("outputs/dynerf-reference/triangulation"))
    parser.add_argument("--output", type=Path, default=Path("outputs/dynerf-reference/localization"))
    args = parser.parse_args()
    localize(args.scene, args.reference, args.output)
