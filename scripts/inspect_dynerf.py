"""Inspect official DyNeRF videos and calibration without importing GPU code.

This checks file consistency, not calibration accuracy or reconstruction quality.
Requires the existing sfm helper dependencies, FFmpeg and FFprobe.
"""
import argparse
import hashlib
import json
import subprocess
import zipfile
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def unpack(archive, destination):
    """Extract only scene videos/calibration, refusing unexpected archive paths."""
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            path = Path(member.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in member.filename:
                raise ValueError("Unsafe archive member")
            if member.is_dir() or path.suffix not in {".mp4", ".npy"}:
                continue
            target = destination / path
            if target.exists():
                if target.stat().st_size != member.file_size:
                    raise ValueError("Partial extraction exists: " + str(target))
                continue
            bundle.extract(member, destination)


def inspect(scene, output):
    videos = sorted(scene.glob("cam*.mp4"))
    calibration_path = scene / "poses_bounds.npy"
    calibration = np.load(calibration_path, allow_pickle=False)
    if len(videos) < 2 or calibration.shape != (len(videos), 17):
        raise ValueError("Expected one 17-value calibration row per sorted video")
    if videos[0].stem != "cam00" or not np.isfinite(calibration).all():
        raise ValueError("Missing held-out cam00 or non-finite calibration")
    poses = calibration[:, :15].reshape(-1, 3, 5)
    rotation = poses[:, :, :3]
    orthogonality = np.max(np.abs(rotation.transpose(0, 2, 1) @ rotation - np.eye(3)))
    determinants = np.linalg.det(rotation)
    # Validate the supplied basis before any loader-specific axis conversion.
    if orthogonality > 1e-3 or not np.allclose(np.abs(determinants), 1, atol=1e-3):
        raise ValueError("Calibration bases are not orthonormal")
    if not np.all(poses[:, :, 4] > 0) or not np.all(calibration[:, 15] > 0):
        raise ValueError("Invalid dimensions, focal lengths or near bounds")
    if not np.all(calibration[:, 16] > calibration[:, 15]):
        raise ValueError("Invalid far bounds")
    records = []
    for index, video in enumerate(videos):
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,duration",
            "-of", "json", str(video)], check=True, capture_output=True)
        stream = json.loads(probe.stdout)["streams"][0]
        height, width, focal = poses[index, :, 4]
        if (stream["width"], stream["height"]) != (int(width), int(height)):
            raise ValueError("Video/calibration dimension mismatch: " + video.name)
        frames = int(stream["nb_frames"])
        if frames < 300 or Fraction(stream["avg_frame_rate"]) != 30:
            raise ValueError("Expected at least 300 frames at 30 FPS")
        records.append(dict(camera=video.stem, calibration_row=index,
                            split="test" if index == 0 else "train",
                            width=int(width), height=int(height), frames=frames,
                            fps=str(stream["avg_frame_rate"]), focal_pixels=float(focal)))
    output.mkdir(parents=True, exist_ok=True)
    selected = np.linspace(0, len(videos) - 1, 6, dtype=int).tolist()
    previews = output / "previews"
    previews.mkdir(exist_ok=True)
    sheet = Image.new("RGB", (6 * 280, 3 * 236), "white")
    draw = ImageDraw.Draw(sheet)
    for column, index in enumerate(selected):
        video = videos[index]
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-threads", "2", "-i", str(video),
            "-vf", "select=eq(n\\,0)+eq(n\\,149)+eq(n\\,299),scale=280:210",
            "-frames:v", "3", "-fps_mode", "vfr",
            str(previews / (video.stem + "-%02d.png"))], check=True)
        for row, frame in enumerate([0, 149, 299]):
            with Image.open(previews / (video.stem + "-%02d.png" % (row + 1))) as im:
                sheet.paste(im, (column * 280, row * 236 + 26))
            label = "%s | %s | frame %d" % (video.stem, records[index]["split"], frame)
            draw.text((column * 280 + 4, row * 236 + 6), label, fill="black")
    sheet.save(output / "contact-sheet.jpg", quality=88)
    report = dict(
        dataset="Neural 3D Video / DyNeRF", scene=scene.name,
        source="https://github.com/facebookresearch/Neural_3D_Video/releases/tag/v1.0",
        license="CC-BY-NC-4.0", calibration_sha256=hashlib.sha256(calibration_path.read_bytes()).hexdigest(),
        cameras=records, train_cameras=len(videos)-1, test_cameras=1,
        upstream_frame_limit=300, upstream_resolution=[1352, 1014],
        upstream_time_rule="frame_index / 300; last frame is 299/300, not 1",
        max_basis_orthogonality_error=float(orthogonality),
        basis_determinant_range=[float(determinants.min()), float(determinants.max())],
        status="File/calibration consistency passed; no GPU training or novel-view evaluation",
        synchronization="Provided by dataset authors; metadata and preview checks do not independently verify it",
        calibration="Author-provided COLMAP estimates, not exact ground-truth camera poses")
    (output / "inspection.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "cameras"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--scene", type=Path, default=Path("data/sample/dynerf/cut_roasted_beef"))
    parser.add_argument("--output", type=Path, default=Path("outputs/dynerf-reference"))
    args = parser.parse_args()
    if args.archive:
        unpack(args.archive, args.scene.parent)
    inspect(args.scene, args.output)
