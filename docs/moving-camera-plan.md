# Moving-camera recommendation

## Source evidence at the pinned upstream commit

[`scripts/extractimages.py`, line 16](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scripts/extractimages.py#L16): `if file_name.startswith("frame_00001")` copies only the first image from each camera into `colmap_tmp/images/imageN.jpg`. It cannot estimate a trajectory.

[`scene/multipleview_dataset.py::load_images_path`, lines 37–53](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/multipleview_dataset.py#L37): the outer `cam_extrinsics` loop computes `R = np.transpose(qvec2rotmat(extr.qvec))` and `T = np.array(extr.tvec)` **before** the inner temporal loop. Every inner iteration appends `image_poses.append((R,T))`. Thus MultipleView cannot represent moving cameras. Its time is `i/image_length`; its test split selects three timestamps from each training camera, with no camera exclusion.

`scene/dataset_readers.py::readMultipleViewinfos` constructs both train/test objects with the same extrinsics. `scene/dataset.py::FourDGSdataset.__getitem__` already accepts a distinct `(image,(R,T),time)` or `CameraInfo` for every sample, so the deformation/rasterization algorithm need not change.

## Options inspected

1. **Background SfM per frame:** estimate `R[c,t],T[c,t]` from the static skatepark. Mask board, fingers, dynamic shadows and HUD where possible; use all synchronized views in a common reconstruction, fixed intrinsics where justified, temporal continuity and broad static overlap. Independent reconstructions per timestamp have unrelated gauges and must not be concatenated. Motion blur, textureless surfaces and game rendering can defeat SfM. Measure registration rate, reprojection error, static landmark consistency and trajectory smoothness.
2. **Thin per-frame loader:** create a project-owned adapter returning the existing per-sample interface, with explicit train/test view lists. This is the smallest safe route when arbitrary intrinsics/resolutions need support. Introduce a narrow loader-dispatch hook only after upstream reproduction; keep it as a documented patch outside the pinned submodule. Do not silently reinterpret MultipleView files.
3. **Existing representations:** `readCamerasFromTransforms` in `dataset_readers.py` reads `frame['transform_matrix']` and `frame['time']` per image. D-NeRF/Blender JSON is the closest simple pose-and-time interchange. `read_timeline` normalizes actual times jointly over train/test. Caveats: loader forces 800x800, uses global horizontal FOV, contains axis/FOV conventions to verify, merges test into training unless `--eval`, and upstream README explicitly warns Blender format may not work. HyperNeRF's `Load_hyper_data` also supplies image-specific cameras/times but carries a larger metadata contract. `readPanopticmeta` natively iterates time then camera with per-sample `k` and `w2c`, but needs `ims`, `train_meta.json`, `test_meta.json`, `init_pt_cld.npz` and a separate camera path. Static COLMAP's `readColmapCameras` assigns time by enumeration; that cannot encode simultaneous views reliably without modification.
4. **Game matrices:** if legitimately accessible later, exported camera matrices, FOV and replay simulation time would remove a large SfM uncertainty. No current game camera export capability has been verified; do not assume one or bypass game protections.

## Proposed contract and smallest first experiment

Use a manifest with `camera_id`, `frame_index`, `image_path`, `timestamp_seconds`, normalized `time`, `width`, `height`, `K`, a 4x4 `world_to_camera`, `split`, distortion model and coordinate convention. Repeated timestamps across cameras are required. Store static initialization point cloud in the same world frame. Normalize times once for the whole clip; reserve one complete camera trajectory as test.

After known D-NeRF reproduction, first attempt a converter to existing D-NeRF JSON with fixed shared intrinsics and explicit `--eval`. Verify the loader's image resizing/coordinate conventions before relying on it. If that fails or intrinsics differ, implement the narrow adapter described above, using explicit per-sample FOV/dimensions and unchanged core optimization. No moving-camera adapter is implemented in this setup.

Validation must include a synthetic moving camera with known poses, reprojection of static landmarks, identical `time` for synchronized samples, a fixed-camera equivalence regression, holdout-ID disjointness, trajectory/FOV continuity, and a short train/render test. Show the loaded camera centers actually change with time; then compare a held-out real trajectory at matched timestamps. A moving object is not evidence that moving camera poses were loaded correctly.
