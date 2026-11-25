"""Preserve static images/projections while moving board seeds beyond CUDA's fixed near plane."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
from prepare_dense_fixed_init import read_cloud,write_cloud
from static_world_scale import training_scale,board_depth_report,require_board_visibility,CUDA_NEAR_DEPTH
from static_board_geometry import project


def prepare(source,output):
    if output.exists():raise ValueError('Choose fresh output')
    original=json.loads((source/'manifest.json').read_text())
    if not original.get('static_scene'):raise ValueError('Static dataset required')
    previous=json.loads((source/'preparation.json').read_text())
    xyz,rgb=read_cloud(source/'points3D_multipleview.ply');start=previous['background_points']
    if len(xyz)!=start+previous['board_seed_points']:raise ValueError('Unexpected seed layout')
    board=xyz[start:]
    factor,minimum=training_scale(board,original['frames'])
    manifest=json.loads(json.dumps(original))
    for record in manifest['frames']:
        pose=np.array(record['world_to_camera']);pose[:,3]*=factor;record['world_to_camera']=pose.tolist()
    scaled=(xyz*factor).astype(np.float32)
    after=require_board_visibility(scaled[start:],manifest['frames'])
    max_delta=0.
    for old,new in zip(original['frames'],manifest['frames']):
        old_uv,z=project(xyz,np.array(old['world_to_camera']),original['intrinsics'])
        new_uv,_=project(scaled,np.array(new['world_to_camera']),original['intrinsics'])
        valid=z>.001
        max_delta=max(max_delta,float(np.abs(old_uv[valid]-new_uv[valid]).max()))
    if max_delta>.001:raise ValueError('Image projections changed during uniform scale')
    output.mkdir(parents=True)
    files=set()
    for record in manifest['frames']:
        for key in ['image_path','evaluation_mask_path','foreground_mask_path']:
            if record.get(key):files.add(record[key])
    hashes={}
    for path in sorted(files):
        src=source/path;dst=output/path;dst.parent.mkdir(parents=True,exist_ok=True)
        try:os.link(src,dst)
        except OSError:shutil.copy2(src,dst)
        hashes[path]=hashlib.sha256(src.read_bytes()).hexdigest()
        assert hashlib.sha256(dst.read_bytes()).hexdigest()==hashes[path]
    write_cloud(output/'points3D_multipleview.ply',scaled,rgb)
    manifest['world_normalization']['scale']/=factor
    guard=dict(cuda_near=CUDA_NEAR_DEPTH,factor=factor,minimum_training_board_depth_before=minimum,
        factor_rule='Next power of two giving training board minimum depth >=0.3; no validation pixels or geometry used to select factor',
        all_seed_views_after=after,projection_max_delta_pixels=max_delta)
    manifest['near_clip_guard']=guard
    preparation=dict(previous,safe_world_scale=guard,source_dataset=str(source),staged_file_sha256=hashes)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'preparation.json').write_text(json.dumps(preparation,indent=2)+'\n')
    (output/'scale-audit.json').write_text(json.dumps(dict(guard,before=board_depth_report(board,original['frames'])),indent=2)+'\n')
    print(json.dumps(guard,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-static-board'))
    p.add_argument('--output',type=Path,default=Path('data/processed/true-skate-static-board-safe'))
    a=p.parse_args();prepare(a.source,a.output)
