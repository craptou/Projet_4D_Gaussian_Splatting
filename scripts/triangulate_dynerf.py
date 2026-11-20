"""Build a sparse DyNeRF initialization from training cameras only, on CPU.

Uses frame 0 and supplied calibration. This is a sparse alternative to upstream
dense COLMAP initialization, not a reproduction of its published results.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pycolmap


def triangulate(scene, output):
    if output.exists():
        raise ValueError("Output exists; choose a fresh destination")
    videos = sorted(scene.glob("cam*.mp4"))
    raw = np.load(scene / "poses_bounds.npy", allow_pickle=False)
    if raw.shape != (len(videos), 17) or videos[0].stem != "cam00":
        raise ValueError("Invalid camera/calibration mapping")
    poses = raw[:, :15].reshape(-1, 3, 5)
    if not np.allclose(poses[:, :, 4], poses[0, :, 4]):
        raise ValueError("Pinned upstream loader assumes shared intrinsics")
    start = time.monotonic()
    images_path = output / "images"
    images_path.mkdir(parents=True)
    for video in videos[1:]:
        subprocess.run(["ffmpeg", "-v", "error", "-threads", "2", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=1352:1014",
                        str(images_path / (video.stem + ".png"))], check=True)
    focal = poses[0, 2, 4] / 2
    db_path = output / "database.db"
    extraction = pycolmap.FeatureExtractionOptions(num_threads=4, max_image_size=1352)
    extraction.sift.max_num_features = 4096
    pycolmap.extract_features(
        db_path, images_path, camera_mode=pycolmap.CameraMode.SINGLE,
        reader_options=pycolmap.ImageReaderOptions(camera_model="SIMPLE_PINHOLE",
            camera_params=f"{focal},676,507"),
        extraction_options=extraction, device=pycolmap.Device.cpu)
    pycolmap.match_exhaustive(db_path,
        matching_options=pycolmap.FeatureMatchingOptions(num_threads=4), device=pycolmap.Device.cpu)
    model_path = output / "known-cameras"
    model_path.mkdir()
    lookup = {video.stem + ".png": poses[i] for i, video in enumerate(videos)}
    with pycolmap.Database.open(db_path) as db:
        cameras = db.read_all_cameras()
        images = db.read_all_images()
    assert all(image.name != "cam00.png" for image in images)
    camera_lines = [f"{cam.camera_id} {cam.model_name} {cam.width} {cam.height} " +
                    " ".join(map(str, cam.params)) for cam in cameras]
    image_lines = []
    supplied = {}
    for image in images:
        pose = lookup[image.name]
        # Exact composition of the axis changes in the pinned Neural3D loader:
        # first [column1, -column0, column2], then [-col0, -col1, -col2]
        # with col0 negated again. Result is OpenCV camera-to-world rotation.
        camera_to_world = np.column_stack([pose[:, 1], pose[:, 0], -pose[:, 2]])
        rotation = camera_to_world.T
        translation = -rotation @ pose[:, 3]
        quaternion = pycolmap.Rotation3d(rotation).quat[[3, 0, 1, 2]]
        transform = np.column_stack([rotation, translation])
        supplied[image.name] = transform
        values = " ".join(map(str, np.concatenate([quaternion, translation])))
        image_lines.append(f"{image.image_id} {values} {image.camera_id} {image.name}\n")
    (model_path / "cameras.txt").write_text("\n".join(camera_lines) + "\n")
    (model_path / "images.txt").write_text("\n".join(image_lines) + "\n")
    (model_path / "points3D.txt").write_text("")
    reconstruction = pycolmap.Reconstruction(model_path)
    options = pycolmap.IncrementalPipelineOptions(num_threads=4, random_seed=0,
        fix_existing_frames=True, ba_refine_focal_length=False,
        ba_refine_extra_params=False, ba_refine_principal_point=False)
    model = pycolmap.triangulate_points(reconstruction, db_path, images_path,
        output / "sparse", options=options, refine_intrinsics=False)
    max_pose_change = max(float(np.abs(image.cam_from_world().matrix() - supplied[image.name]).max())
                          for image in model.images.values())
    if max_pose_change > 1e-8 or model.num_points3D() == 0:
        raise ValueError("Fixed-pose triangulation failed; inspect partial output")
    model.export_PLY(output / "points3D_downsample2.ply")
    result = dict(scene=scene.name, pycolmap_version=pycolmap.__version__,
        device="CPU", source_frame=0, image_resolution=[1352, 1014],
        training_cameras=sorted(image.name for image in images), excluded_camera="cam00",
        registered_images=model.num_reg_images(), points3D=model.num_points3D(),
        mean_reprojection_error_pixels=model.compute_mean_reprojection_error(),
        mean_track_length=model.compute_mean_track_length(), max_pose_change=max_pose_change,
        elapsed_seconds=time.monotonic()-start,
        initialization="Sparse SIFT triangulation at supplied fixed poses; no dense stereo or downsampling",
        calibration_provenance="Author-provided full-rig calibration; cam00 pixels excluded from this triangulation",
        status="Geometry preparation only; no dynamic training/rendering or quality metrics")
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, default=Path("data/sample/dynerf/cut_roasted_beef"))
    parser.add_argument("--output", type=Path, default=Path("outputs/dynerf-reference/triangulation"))
    args = parser.parse_args()
    triangulate(args.scene, args.output)
