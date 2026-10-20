"""Explicit camera model gate; motion is capture metadata, not inferred here."""


def require_fixed(meta):
    if meta.get("camera_motion") != "fixed":
        raise ValueError("MOVING_CAMERA cannot use upstream MultipleView: per-frame poses required")
