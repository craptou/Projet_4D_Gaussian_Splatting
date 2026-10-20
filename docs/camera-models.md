# Camera models

Intrinsics `K = [[fx,0,cx],[0,fy,cy],[0,0,1]]` map camera coordinates to pixels. For world point `X`, `lambda * [u,v,1]^T = K (R X + T)`. Extrinsics `[R | T]` here are **world-to-camera**; the camera center in world coordinates is `C = -R^T T`. A camera-to-world pose is the inverse transform, not the same matrix.

For a fixed camera c, use `R_c,T_c` for every timestamp. For a moving camera, require `R_{c,t},T_{c,t}`; zoom can also require `K_{c,t}`. Matching frame indexes does not supply these matrices. SfM recovers geometry up to a similarity transform; preserve one common scale/world frame across cameras and time.

The upstream MultipleView loader stores transposed COLMAP rotation and direct tvec (`R = qvec2rotmat(qvec).T`, `T = extr.tvec`) for its internal convention. Do not pass a raw world-to-camera rotation into that field unchanged. The D-NeRF JSON loader expects camera-to-world matrices and applies its own axis conversion. Verify conversions with projected landmarks and a synthetic known pose.

Additional upstream limitation: `multipleview_dataset.__init__` reads `cam_intrinsics[1]` and uses its first focal parameter for both axes and every camera. Our wrapper explicitly requests a single `SIMPLE_PINHOLE` calibration. This is suitable only for matched centered, undistorted views. Variable FOV, off-center crops, distortion, or different resolutions require a reviewed loader/intrinsics change. Inspect fitted focal lengths and reprojection errors; never force an invalid camera model just to make training load.

COLMAP was not found (`colmap -h` attempted); version/CUDA status remain unknown. See `environment/README.md` for binary/container installation options and dense-CUDA requirements.
