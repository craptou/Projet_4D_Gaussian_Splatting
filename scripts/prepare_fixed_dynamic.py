"""Prepare a small centered crop with calibrated poses and event-based offsets."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw
import pycolmap

TRAINING = ["cam01", "cam02", "cam03", "cam06", "cam07", "cam08", "cam10", "cam12"]


def prepare(output):
    if output.exists():
        raise ValueError("Output exists; choose a fresh directory")
    reference = Path("outputs/fixed-geometry-2026-11-24")
    model = pycolmap.Reconstruction(reference/"sparse/1")
    holdout = json.loads(Path("outputs/fixed-dynamic-preparation/holdout.json").read_text())
    current_map = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (reference/"sparse/1").glob("*.bin")}
    if current_map != holdout["map_sha256"]:
        raise ValueError("Frozen background map changed since holdout localization")
    events = json.loads(Path("outputs/fixed-dynamic-preparation/events-v2.json").read_text())
    if not holdout["accepted"]:
        raise ValueError("Holdout localization did not pass")
    offsets = {r["camera_id"]: r["suggested_source_frame_offset"] for r in events["cameras"]}
    if max(r["offset_disagreement_frames"] for r in events["cameras"]) > 1:
        raise ValueError("UI events disagree on a constant alignment shift")
    camera = next(iter(model.cameras.values()))
    f,cx,cy = camera.params
    # Centered crop preserves the estimated principal point for the stock
    # renderer, which does not support an arbitrary principal-point offset.
    x,y,w,h = 0,818,1126,800
    assert np.allclose([cx-x,cy-y], [w/2,h/2])
    width,height = 563,400
    resized_focal = f/2
    indices = list(range(522,547,2))  # 8.7 through 9.1 seconds, 30 samples/sec.
    poses = {im.name.removesuffix(".png"): im.cam_from_world().matrix().tolist() for im in model.images.values()}
    assert "cam13" not in poses
    poses["cam13"] = holdout["world_to_camera"]
    output.mkdir(parents=True)
    records = []
    contact = Image.new("RGB", (3*width,(len(TRAINING)+1)*(height+25)), "white")
    draw = ImageDraw.Draw(contact)
    for row,name in enumerate(TRAINING+["cam13"]):
        actual = [i+offsets[name] for i in indices]
        select = "+".join(f"eq(n\\,{i})" for i in actual)
        raw = subprocess.check_output(["ffmpeg", "-nostdin", "-v", "error", "-i",
            f"data/raw/true-skate-fixed-2026-11-23/{name}.mp4", "-vf",
            f"select={select},crop={w}:{h}:{x}:{y},scale={width}:{height}", "-frames:v", str(len(indices)),
            "-fps_mode", "passthrough", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"])
        size = width*height*3
        assert len(raw) == size*len(indices)
        (output/"images"/name).mkdir(parents=True)
        for j,index in enumerate(actual):
            image = Image.frombytes("RGB", (width,height), raw[j*size:(j+1)*size])
            path = f"images/{name}/{j:03d}.png"
            image.save(output/path, compress_level=3)
            records.append(dict(camera_id=name, image_path=path, time=j/(len(indices)-1),
                clip_frame=index, aligned_clip_seconds=indices[j]/60,
                split="test" if name=="cam13" else "train", world_to_camera=poses[name]))
            if j in [0,6,12]:
                column = [0,6,12].index(j)
                contact.paste(image, (column*width,row*(height+25)+25))
                draw.text((column*width+5,row*(height+25)+5),f"{name} | aligned {indices[j]/60:.2f}s | source frame {index}",fill="black")
    # Training-only sparse initialization, with explicit support filtering.
    selected = [p for p in model.points3D.values() if p.track.length()>=3 and p.error<=2]
    xyz = np.array([p.xyz for p in selected], dtype=np.float32)
    rgb = np.array([p.color for p in selected], dtype=np.uint8)
    assert len(xyz)>=300
    # Rescale the arbitrary map to a compact extent for the deformation grid.
    centers = np.array([-np.array(poses[n])[:,:3].T @ np.array(poses[n])[:,3] for n in TRAINING])
    origin = centers.mean(0)
    scale = float(np.max(np.linalg.norm(centers-origin,axis=1)))
    xyz = (xyz-origin)/scale
    for record in records:
        matrix = np.array(record["world_to_camera"])
        matrix[:,3] = (matrix[:,:3]@origin+matrix[:,3])/scale
        record["world_to_camera"] = matrix.tolist()
    vertices = np.zeros(len(xyz), dtype=[(k,"<f4") for k in ["x","y","z","nx","ny","nz"]]+[(k,"u1") for k in ["red","green","blue"]])
    for i,key in enumerate(["x","y","z"]): vertices[key]=xyz[:,i]
    for i,key in enumerate(["red","green","blue"]): vertices[key]=rgb[:,i]
    header = f"ply\nformat binary_little_endian 1.0\nelement vertex {len(xyz)}\n"
    header += "".join(f"property float {k}\n" for k in ["x","y","z","nx","ny","nz"])
    header += "".join(f"property uchar {k}\n" for k in ["red","green","blue"])
    (output/"points3D_multipleview.ply").write_bytes((header+"end_header\n").encode()+vertices.tobytes())
    contact.save(output/"contact-sheet.jpg", quality=90)
    result = dict(training_cameras=TRAINING, heldout_camera="cam13", frames=records,
        image_resolution=[width,height], intrinsics=[resized_focal,width/2,height/2],
        crop_xywh=[x,y,w,h], source_frame_indices_before_offsets=indices, source_fps=60,
        sample_fps=30, first_last_aligned_seconds=[8.7,9.1], physical_time_span_seconds=.4,
        normalized_time_rule="sample index / 12; physical replay span 0.4 seconds",
        source_frame_offsets=offsets, initialization_points=len(xyz),
        initialization="Training-only background map, track length >=3 and point error <=2 pixels; no board-specific seeds",
        world_normalization=dict(origin=origin.tolist(),scale=scale),
        limitations="UI-event-based alignment, not proven simulation synchronization. Shortened to avoid bottom HUD. Shared estimated lens calibration. No board mask/segmentation in training.")
    (output/"manifest.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!='frames'},indent=2),flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("data/processed/true-skate-fixed-pilot-v2"))
    args=parser.parse_args()
    prepare(args.output)
