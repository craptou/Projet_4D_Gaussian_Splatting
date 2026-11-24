"""Bounded static-background SfM check for the recovered fixed True Skate views."""
import argparse
import json
from pathlib import Path
import subprocess
import time

from PIL import Image, ImageDraw
import numpy as np
import pycolmap


def run(clips, output, seconds):
    if output.exists():
        raise ValueError("Choose a fresh output directory")
    cuts = json.loads((clips / "cuts.json").read_text())
    names = cuts["distinct_sampled_fixed_views"]
    # Reserve before matching/mapping. This is independent of the earlier dataset.
    holdout = names[-1]
    training = names[:-1]
    output.mkdir(parents=True)
    images = output / "images"
    images.mkdir()
    mask = Image.new("L", (1126, 1700), 255)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((0, 0, 180, 150), fill=0)
    draw.rectangle((850, 350, 1125, 620), fill=0)
    mask.save(output / "background-mask.png")
    for name in names:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", "5.3", "-i",
            str(clips / (name + ".mp4")), "-vf", "crop=1126:1700:0:0", "-frames:v", "1",
            "-y", str(images / (name + ".png"))], check=True)
    started = time.monotonic()
    database = output / "database.db"
    reader = pycolmap.ImageReaderOptions(camera_model="SIMPLE_PINHOLE",
        camera_params="2040,563,1218", camera_mask_path=output / "background-mask.png")
    extraction = pycolmap.FeatureExtractionOptions(num_threads=4, max_image_size=1700)
    extraction.sift.max_num_features = 4096
    print("Extracting background features from", len(training), "training views; holdout", holdout, flush=True)
    pycolmap.extract_features(database, images, image_names=[n + ".png" for n in training],
        camera_mode=pycolmap.CameraMode.SINGLE, reader_options=reader,
        extraction_options=extraction, device=pycolmap.Device.cpu)
    print("Matching and bounded mapping", flush=True)
    pycolmap.match_exhaustive(database,
        matching_options=pycolmap.FeatureMatchingOptions(num_threads=4), device=pycolmap.Device.cpu)
    options = pycolmap.IncrementalPipelineOptions(num_threads=4, random_seed=0,
        max_num_models=3, min_model_size=3, max_runtime_seconds=seconds,
        ba_refine_principal_point=False)
    models = pycolmap.incremental_mapping(database, images, output / "sparse", options=options)
    summaries = []
    for index, model in models.items():
        registered = [image.name for image in model.images.values() if image.has_pose]
        assert holdout + ".png" not in registered
        summaries.append(dict(model_id=index, registered_images=len(registered), names=sorted(registered),
            points3D=model.num_points3D(), mean_reprojection_error=model.compute_mean_reprojection_error(),
            mean_track_length=model.compute_mean_track_length(),
            cameras={str(k): camera.params.tolist() for k, camera in model.cameras.items()}))
        model.export_PLY(output / f"model-{index}.ply")
    report = dict(source_sha256=cuts["source_sha256"], training_views=training, reserved_holdout=holdout,
        holdout_used_in_mapping=False, models=summaries, elapsed_seconds=time.monotonic()-started,
        assumptions="Shared SIMPLE_PINHOLE; focal initialized at 2040 and optimized; original principal point fixed at (563,1218); top-left crop 1126x1700; HUD mask only, no explicit board mask.",
        limitations="Sparse static-background feasibility only. No temporal synchronization validation, held-out rendering, metric scale, board reconstruction or 4D training.")
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


def diagnose(output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    report = json.loads((output / "report.json").read_text())
    if not report["models"]:
        return
    selected = max(report["models"], key=lambda m: m["registered_images"])
    model = pycolmap.Reconstruction(output / "sparse" / str(selected["model_id"]))
    angles = []
    for point in model.points3D.values():
        rays = np.array([model.image(e.image_id).projection_center()-point.xyz for e in point.track.elements])
        rays /= np.linalg.norm(rays, axis=1)[:, None]
        angles.append(float(np.degrees(np.arccos(np.clip(rays @ rays.T, -1, 1))).max()))
    diagnostics = dict(selected_model=selected["model_id"], selection="Most registered training views; exploratory selection, not independent validation",
        point_reprojection_error_p50_p90_p95=np.percentile([p.error for p in model.points3D.values()], [50,90,95]).tolist(),
        maximum_triangulation_angle_per_point_p10_p50_p90_degrees=np.percentile(angles,[10,50,90]).tolist(),
        caution="Other mapper hypotheses and solver warnings must be reviewed; low image residual does not establish physical accuracy. World coordinates have arbitrary scale/orientation.")
    (output / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2)+"\n")
    xyz = np.array([point.xyz for point in model.points3D.values()])
    low, high = np.percentile(xyz, [2,98], axis=0)
    visible = xyz[np.all((xyz >= low) & (xyz <= high), axis=1)]
    fig = plt.figure(figsize=(9,7))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(*visible.T, s=2, alpha=.45, color="gray", label="Sparse scene (outer 2% per axis omitted)")
    for image in model.images.values():
        if image.has_pose:
            center = image.projection_center()
            ax.scatter(*center, color="royalblue", s=25)
            ax.text(*center, image.name.removesuffix(".png"), fontsize=8)
    ax.set(xlabel="World X", ylabel="World Y", zlabel="World Z",
        title=f"Fixed-view geometry pilot: {selected['registered_images']} cameras / {selected['points3D']} points\nArbitrary units and orientation; background only; holdout excluded")
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "geometry.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clips", type=Path, default=Path("data/raw/true-skate-fixed-2026-11-23"))
    parser.add_argument("--output", type=Path, default=Path("outputs/fixed-geometry-2026-11-24"))
    parser.add_argument("--max-mapping-seconds", type=int, default=120)
    args = parser.parse_args()
    if args.max_mapping_seconds <= 0:
        parser.error("Mapping budget must be positive")
    run(args.clips, args.output, args.max_mapping_seconds)
    diagnose(args.output)
