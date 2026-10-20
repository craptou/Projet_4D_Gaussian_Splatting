# Deterministic capture protocol

1. Save one replay and assign a replay ID. Capture the same deterministic replay for every view; never perform the trick again for another camera.
2. Disable HUD, auto zoom, dynamic FOV, stabilization, motion blur and frame interpolation where the game permits. Record actual settings and versions; do not assume these options exist.
3. Test whether the editor offers a genuinely stationary camera. Inspect background landmarks across the entire clip. A Follow/Orbit/Custom label is not evidence of fixed extrinsics. Declare moving motion if uncertain.
4. Capture overlapping, separated viewpoints with a visible static skatepark background. Lock aspect ratio, FOV, resolution and constant FPS. Choose a sharp reference instant with sufficient static texture; dynamic board/fingers can corrupt first-frame SfM correspondences.
5. Use an identifiable replay start/end state and the same duration. Record any synchronization offsets separately; align explicitly before extraction. Screen recorder timestamps are not game simulation timestamps: look for skipped/duplicated replay states even when FFprobe reports constant FPS.
6. Reserve a real game camera as holdout before reconstruction. Inspect generated contact sheets at first/middle/last and additional fast-motion instants. Reject inconsistent board orientation/contact events. Save the review and synchronization evidence with the experiment.

Fixed cameras must keep **both pose and intrinsics** constant. The current upstream wrapper additionally assumes one shared centered square-pixel focal length across all cameras. Moving capture is accepted for storage/inspection, then blocked at fixed-camera preprocessing.
