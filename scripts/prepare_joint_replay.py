"""Assemble three safe static datasets into one training-only-initialized temporal scene."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
from prepare_dense_fixed_init import read_cloud
from static_world_scale import require_board_visibility


def normalized_times(seconds):
    values=np.asarray(seconds,dtype=float)
    if values.ndim!=1 or len(values)<2 or not np.isfinite(values).all() or np.any(np.diff(values)<=0):
        raise ValueError('Physical instants must be finite and strictly increasing')
    return ((values-values[0])/(values[-1]-values[0])).tolist()


def prepare(sources,output):
    if len(sources)!=3:raise ValueError('Expected exactly three ordered static datasets')
    if output.exists():raise ValueError('Choose fresh output')
    manifests=[json.loads((p/'manifest.json').read_text()) for p in sources]
    preparations=[json.loads((p/'preparation.json').read_text()) for p in sources]
    if any(p['heldout_used_for_seeds'] for p in preparations):raise ValueError('Reserved-view initialization leakage')
    canonical=manifests[0]
    seconds=[next(iter({r['seconds_relative_to_score'] for r in m['frames']})) for m in manifests]
    times=normalized_times(seconds)
    def geometry(m):
        return dict(cameras=m['training_cameras'],heldout=m['heldout_camera'],intrinsics=m['intrinsics'],size=m['image_resolution'],
            normalization=m['world_normalization'],poses={r['camera_id']:r['world_to_camera'] for r in m['frames']})
    if any(geometry(m)!=geometry(canonical) for m in manifests):raise ValueError('Camera geometry or world normalization differs')
    if any(len({r['seconds_relative_to_score'] for r in m['frames']})!=1 for m in manifests):raise ValueError('Expected single-instant source datasets')
    for m in manifests:
        if not m.get('static_scene') or not m.get('near_clip_guard'):raise ValueError('Safe static sources required')
    output.mkdir(parents=True)
    hashes={};frames=[]
    def stage(src,dst):
        dst.parent.mkdir(parents=True,exist_ok=True)
        try:os.link(src,dst)
        except OSError:shutil.copy2(src,dst)
        digest=hashlib.sha256(src.read_bytes()).hexdigest()
        if hashlib.sha256(dst.read_bytes()).hexdigest()!=digest:raise ValueError('File changed while staging')
        hashes[str(dst.relative_to(output))]=digest
    for source,manifest,time in zip(sources,manifests,times):
        sample=manifest['sample_index']
        for original in manifest['frames']:
            record=json.loads(json.dumps(original));name=record['camera_id']
            record['time']=time;record['sample_index']=sample
            stage(source/record['image_path'],output/record['image_path'])
            path=f'masks/{name}/{sample:03d}.png'
            stage(source/record['evaluation_mask_path'],output/path)
            record['evaluation_mask_path']=path
            if original.get('foreground_mask_path'):
                if record['split']!='train':raise ValueError('Heldout image cannot supply foreground training mask')
                record['foreground_mask_path']=path
            frames.append(record)
    frames.sort(key=lambda r:(r['split']!='train',r['camera_id'],r['time']))
    if any(r['camera_id']==canonical['heldout_camera'] and r['split']=='train' for r in frames):raise ValueError('Camera split leakage')
    stage(sources[0]/'points3D_multipleview.ply',output/'points3D_multipleview.ply')
    xyz,_=read_cloud(output/'points3D_multipleview.ply');start=preparations[0]['background_points'];count=preparations[0]['board_seed_points']
    visibility=require_board_visibility(xyz[start:start+count],frames)
    result=dict(canonical,static_scene=False,temporal_scene=True,frames=frames,
        sample_indices=[m['sample_index'] for m in manifests],normalized_times=times,
        physical_time_span_seconds=seconds[-1]-seconds[0],frozen_control_time=times[1],
        normalized_time_rule='(seconds_relative_to_score - first physical instant) / physical span; nonuniform spacing retained',
        initialization='Untrained background + silhouette-volume seeds from first physical instant only; no trained static weights or validation seeds',
        foreground_loss=dict(weight=.1,masked_training_images=sum(bool(r.get('foreground_mask_path')) for r in frames),
            rule='Full-image L1 +0.1*foreground mean L1 on available training masks only'),
        limitations='Three observed instants, same repeated validation camera, approximate masks; no interpolation or physical tracking validation.')
    result.pop('sample_index',None)
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    preparation=dict(background_points=start,board_seed_points=count,canonical_sample=manifests[0]['sample_index'],
        sample_indices=result['sample_indices'],normalized_times=times,seconds_relative_to_score=seconds,
        train_images=sum(r['split']=='train' for r in frames),validation_images=sum(r['split']=='test' for r in frames),
        masks_used=result['foreground_loss']['masked_training_images'],heldout_used_for_seeds=False,
        source_manifest_sha256={str(p):hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest() for p in sources},
        staged_file_sha256=hashes,canonical_seed_visibility=visibility)
    (output/'preparation.json').write_text(json.dumps(preparation,indent=2)+'\n')
    print(json.dumps({k:v for k,v in preparation.items() if k not in ['staged_file_sha256','source_manifest_sha256','canonical_seed_visibility']},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources',type=Path,nargs='+',default=[Path('data/processed/true-skate-static-sample03-safe'),Path('data/processed/true-skate-static-board-safe'),Path('data/processed/true-skate-static-sample12-safe')])
    p.add_argument('--output',type=Path,default=Path('data/processed/true-skate-joint-three'))
    a=p.parse_args();prepare(a.sources,a.output)
