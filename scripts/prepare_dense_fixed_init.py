"""Resample training-only sparse points; keep the existing images and poses.

Interpolated samples are an initialization hypothesis, not new observations.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np

FIELDS = [(k,"<f4") for k in ["x","y","z","nx","ny","nz"]]+[(k,"u1") for k in ["red","green","blue"]]


def read_cloud(path):
    with path.open("rb") as handle:
        header=[]
        while True:
            line=handle.readline()
            if not line or len(header)>100:
                raise ValueError("Invalid PLY header")
            header.append(line.decode("ascii").strip())
            if header[-1]=="end_header": break
        count=[int(line.split()[-1]) for line in header if line.startswith("element vertex ")]
        properties=[line.split()[1:] for line in header if line.startswith("property ")]
        expected=[["float",k] for k in ["x","y","z","nx","ny","nz"]]+[["uchar",k] for k in ["red","green","blue"]]
        if "format binary_little_endian 1.0" not in header or len(count)!=1 or properties!=expected:
            raise ValueError("Expected the project's binary training initialization PLY")
        raw=handle.read()
    if len(raw)!=count[0]*np.dtype(FIELDS).itemsize:
        raise ValueError("PLY vertex data length differs from its header")
    vertices=np.frombuffer(raw,dtype=FIELDS).copy()
    return np.column_stack([vertices[k] for k in ["x","y","z"]]),np.column_stack([vertices[k] for k in ["red","green","blue"]])


def resample(xyz,rgb,factor=8,seed=24):
    if not 2<=factor<=16 or len(xyz)<7 or not np.isfinite(xyz).all():
        raise ValueError("Need finite points, at least 7 samples, and a factor from 2 to 16")
    # Find six nearest distinct points without allocating a giant N*N*3 array.
    points=np.asarray(xyz,dtype=np.float64)
    nearest=[]
    for start in range(0,len(points),256):
        delta=points[start:start+256,None,:]-points[None,:,:]
        distance=(delta*delta).sum(2)
        distance[distance<1e-16]=np.inf
        neighbors=np.argpartition(distance,5,axis=1)[:,:6]
        order=np.argsort(np.take_along_axis(distance,neighbors,axis=1),axis=1,kind="stable")
        nearest.append(np.take_along_axis(neighbors,order,axis=1))
    nearest=np.concatenate(nearest)
    rng=np.random.default_rng(seed)
    parents=np.repeat(np.arange(len(points)),factor-1)
    choices=rng.integers(0,6,len(parents))
    neighbors=nearest[parents,choices]
    weights=rng.uniform(.1,.9,(len(parents),1))
    children=(1-weights)*points[parents]+weights*points[neighbors]
    colors=(1-weights)*rgb[parents]+weights*rgb[neighbors]
    return np.concatenate([points,children]).astype(np.float32),np.concatenate([rgb,colors]).round().clip(0,255).astype(np.uint8)


def write_cloud(path,xyz,rgb):
    vertices=np.zeros(len(xyz),dtype=FIELDS)
    for i,key in enumerate(["x","y","z"]):vertices[key]=xyz[:,i]
    for i,key in enumerate(["red","green","blue"]):vertices[key]=rgb[:,i]
    header=f"ply\nformat binary_little_endian 1.0\nelement vertex {len(xyz)}\n"
    header+="".join(f"property float {k}\n" for k in ["x","y","z","nx","ny","nz"])
    header+="".join(f"property uchar {k}\n" for k in ["red","green","blue"])
    path.write_bytes((header+"end_header\n").encode()+vertices.tobytes())


def prepare(source,output,factor=8):
    if output.exists():raise ValueError("Output exists; choose a fresh experiment directory")
    original=json.loads((source/"manifest.json").read_text())
    assert original["heldout_camera"] not in original["training_cameras"]
    xyz,rgb=read_cloud(source/"points3D_multipleview.ply")
    if len(xyz)!=original["initialization_points"]:raise ValueError("Input cloud count differs from manifest")
    dense,colors=resample(xyz,rgb,factor)
    output.mkdir(parents=True)
    copied=0
    for record in original["frames"]:
        src=source/record["image_path"];dest=output/record["image_path"]
        dest.parent.mkdir(parents=True,exist_ok=True)
        try:os.link(src,dest)
        except OSError:shutil.copy2(src,dest);copied+=1
        if hashlib.sha256(src.read_bytes()).digest()!=hashlib.sha256(dest.read_bytes()).digest():
            raise ValueError("Image pixels changed during staging")
    write_cloud(output/"points3D_multipleview.ply",dense,colors)
    report=dict(method="Original points retained plus color/position interpolation along six-nearest-neighbor segments",
        original_points=len(xyz),resampled_points=len(dense),factor=factor,seed=24,
        source_manifest_sha256=hashlib.sha256((source/"manifest.json").read_bytes()).hexdigest(),
        source_cloud_sha256=hashlib.sha256((source/"points3D_multipleview.ply").read_bytes()).hexdigest(),
        images_verified_identical=len(original["frames"]),images_copied_instead_of_linked=copied,
        heldout_pixels_used_for_point_generation=False,
        caution="Synthetic initialization samples, not new triangulated observations. Segments can cross surface/depth discontinuities. This changes point count and spatial/color distribution, not only count.")
    manifest=dict(original,initialization_points=len(dense),initialization=report["method"],resampling=report)
    assert manifest["frames"]==original["frames"]
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (output/"preparation.json").write_text(json.dumps(report,indent=2)+"\n")
    print(f"Points initiaux : {len(xyz)} -> {len(dense)}; {len(original['frames'])} images identiques, poses/temps inchanges.",flush=True)
    print("Ces nouveaux points sont interpoles, pas de nouvelles mesures 3D.",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--factor",type=int,default=8,choices=range(2,17))
    args=parser.parse_args()
    prepare(args.source,args.output,args.factor)
