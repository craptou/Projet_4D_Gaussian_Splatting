"""Bounded adaptation of pinned Dynamic3DGaussians; original losses except unknown floor disabled."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import sys
import time
import types

import numpy as np
from PIL import Image

from prepare_dense_fixed_init import read_cloud

UPSTREAM=Path('/root/skate4d/Dynamic3DGaussians')
METHOD_SHA='7dbbd4dec404308524ff402756bdb8143a2589b0'


def reference():
    import subprocess
    if subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()!=METHOD_SHA:raise ValueError('Unexpected upstream revision')
    sys.path.insert(0,str(UPSTREAM))
    source=(UPSTREAM/'train.py').read_text()
    anchor="'floor': 2.0"
    if source.count(anchor)!=1:raise ValueError('Unknown upstream floor-loss implementation')
    module=types.ModuleType('dynamic_reference')
    exec(compile(source.replace(anchor,"'floor': 0.0"),str(UPSTREAM/'train.py'),'exec'),module.__dict__)
    original=module.setup_camera
    def camera(w,h,k,w2c,near=.01,far=100):return original(w,h,k,w2c,near=.01,far=far)
    module.setup_camera=camera
    return module


def export(source,work):
    manifest=json.loads((source/'manifest.json').read_text())
    if not manifest.get('temporal_scene'):raise ValueError('Expected temporal source')
    frames=manifest['frames'];cameras=manifest['training_cameras'];samples=manifest['sample_indices']
    if manifest['heldout_camera'] in cameras:raise ValueError('Reserved-view leakage')
    records={(r['camera_id'],r['sample_index']):r for r in frames}
    width,height=manifest['image_resolution'];f,cx,cy=manifest['intrinsics']
    k=[[f,0,cx],[0,f,cy],[0,0,1]];metadata=dict(w=width,h=height,fn=[],k=[],w2c=[])
    destination=work/'data/replay';destination.mkdir(parents=True)
    for sample in samples:
        names=[];poses=[]
        for name in cameras:
            record=records[name,sample]
            if record['split']!='train' or not record.get('foreground_mask_path'):raise ValueError('Every optimization image needs its training mask')
            with Image.open(source/record['image_path']) as im:
                if im.size!=(width,height):raise ValueError('RGB dimensions differ from calibration')
            filename=f'{name}/{sample:03d}.png';names.append(filename)
            image=destination/'ims'/filename;image.parent.mkdir(parents=True,exist_ok=True)
            try:os.link(source/record['image_path'],image)
            except OSError:shutil.copy2(source/record['image_path'],image)
            with Image.open(source/record['foreground_mask_path']) as im:mask=(np.array(im.convert('L'))>0).astype(np.uint8)
            if mask.shape!=(height,width):raise ValueError('Mask dimensions differ from calibration')
            if mask.sum()<=20:raise ValueError('Unusable optimization mask')
            seg=destination/'seg'/filename;seg.parent.mkdir(parents=True,exist_ok=True)
            Image.fromarray(mask).save(seg)
            poses.append(record['world_to_camera']+[[0,0,0,1]])
        metadata['fn'].append(names);metadata['k'].append([k]*len(cameras));metadata['w2c'].append(poses)
    (destination/'train_meta.json').write_text(json.dumps(metadata)+'\n')
    xyz,rgb=read_cloud(source/'points3D_multipleview.ply')
    prep=json.loads((source/'preparation.json').read_text());roles=(np.arange(len(xyz))>=prep['background_points']).astype(np.float32)
    np.savez(destination/'init_pt_cld.npz',data=np.c_[xyz,rgb.astype(np.float32)/255,roles].astype(np.float32))
    return manifest,metadata


def projection_probe(module,manifest,metadata):
    from static_world_scale import require_board_visibility
    source=Path(manifest['_source']);xyz,_=read_cloud(source/'points3D_multipleview.ply')
    prep=json.loads((source/'preparation.json').read_text());board=xyz[prep['background_points']:]
    visibility=require_board_visibility(board,manifest['frames']);maximum=0.
    for k,pose in zip(metadata['k'][0],metadata['w2c'][0]):
        camera=module.setup_camera(metadata['w'],metadata['h'],np.array(k),np.array(pose))
        cp=board@np.array(pose)[:3,:3].T+np.array(pose)[:3,3]
        expected=cp[:,:2]/cp[:,2,None]*manifest['intrinsics'][0]+manifest['intrinsics'][1:]
        clip=np.c_[board,np.ones(len(board))]@camera.projmatrix.detach().cpu().numpy()[0]
        projected=(clip[:,:2]/clip[:,3,None]+1)*np.array(manifest['image_resolution'])/2
        maximum=max(maximum,float(np.abs(projected-expected).max()))
    if maximum>.001:raise ValueError('Dynamic renderer camera projection mismatch')
    return dict(projection_max_error_pixels=maximum,initial_actor_visibility=visibility,python_near=.01,
        note='Canonical actor seeds only; no all-point visibility guarantee after optimization.')


def train(source,output,initial_steps=2000,subsequent_steps=400):
    import torch
    if initial_steps<1 or subsequent_steps<1:raise ValueError('Iteration budgets must be positive')
    if output.exists():raise ValueError('Choose fresh output')
    output.mkdir(parents=True);work=output/'work';work.mkdir()
    source=source.resolve();manifest,metadata=export(source,work);manifest['_source']=str(source)
    module=reference();random.seed(24);np.random.seed(24);torch.manual_seed(24);torch.cuda.manual_seed_all(24)
    os.chdir(work)
    probe=projection_probe(module,manifest,metadata)
    (output/'loader.json').write_text(json.dumps(probe,indent=2)+'\n')
    params,variables=module.initialize_params('replay',metadata)
    optimizer=module.initialize_optimizer(params,variables);output_params=[];timings=[]
    torch.cuda.reset_peak_memory_stats();started=time.monotonic()
    for t,sample in enumerate(manifest['sample_indices']):
        tick=time.monotonic();dataset=module.get_dataset(t,metadata,'replay');todo=[]
        if t:params,variables=module.initialize_per_timestep(params,variables,optimizer)
        steps=subsequent_steps if t else initial_steps
        for i in range(steps):
            current=module.get_batch(todo,dataset);loss,variables=module.get_loss(params,current,variables,t==0)
            if not torch.isfinite(loss):raise ValueError('Nonfinite Dynamic3DGaussians loss')
            loss.backward()
            with torch.no_grad():
                # Bounded first-frame density schedule for 6GB GPU; no later births.
                if t==0 and i<=1200 and len(params['means3D'])<20000:
                    params,variables=module.densify(params,variables,optimizer,i)
                optimizer.step();optimizer.zero_grad(set_to_none=True)
            if i%100==0 or i+1==steps:
                elapsed=time.monotonic()-tick
                eta=(steps-i-1)*elapsed/(i+1)
                print(f'Dynamic frame {t+1}/10 sample{sample} step {i+1}/{steps} loss={loss.item():.5f} points={len(params["means3D"])} elapsed={elapsed:.1f}s remaining-frame~{eta:.1f}s',flush=True)
        output_params.append(module.params2cpu(params,t==0))
        (output/'states').mkdir(exist_ok=True)
        np.savez(output/'states'/f'{sample:03d}.npz',**{key:value.detach().cpu().numpy() for key,value in params.items()})
        timings.append(time.monotonic()-tick)
        if t==0:
            count=int((params['seg_colors'][:,0]>.5).sum())
            if count<=20:raise ValueError('Too few actor descendants after initialization')
            variables=module.initialize_post_first_timestep(params,variables,optimizer)
    training_seconds=time.monotonic()-started
    module.save_params(output_params,'replay','bounded')
    report=dict(method='Dynamic3DGaussians',upstream_sha=METHOD_SHA,
        rasterizer_sha='cb65e4b86bc3bd8ed42174b72a62e8d3a3a71110',initial_steps=initial_steps,subsequent_steps=subsequent_steps,
        total_iterations=initial_steps+subsequent_steps*(len(timings)-1),training_seconds=training_seconds,frame_seconds=timings,
        gpu=torch.cuda.get_device_name(),peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
        gaussian_count=len(params['means3D']),actor_descendants=int((params['seg_colors'][:,0]>.5).sum()),
        training_cameras=manifest['training_cameras'],heldout_camera=manifest['heldout_camera'],samples=manifest['sample_indices'],
        input_manifest_sha256=hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),
        initialization_sha256=hashlib.sha256((source/'points3D_multipleview.ply').read_bytes()).hexdigest(),
        adaptations=['Unknown ground plane: floor loss disabled','Python near plane .01, same canonical projection/depth gate as 4DGS',
          f'{initial_steps} initial /{subsequent_steps} subsequent steps instead of official10000/2000','Initial densification only through1200 steps, attempted only below20000 points',
          'Existing synthetic silhouette-volume initialization, not depth-camera points'],
        limitations='Bounded feasibility adaptation, not reproduction of published results. Candidate masks and seed roles approximate. All ten times supervised. No physical tracking truth or untouched test camera.')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


def render(source,output):
    import torch
    module=reference();manifest=json.loads((source/'manifest.json').read_text());samples=manifest['sample_indices']
    frames=manifest['frames'];width,height=manifest['image_resolution'];f,cx,cy=manifest['intrinsics'];k=np.array([[f,0,cx],[0,f,cy],[0,0,1]])
    timeline=output/'timeline';timeline.mkdir(exist_ok=True)
    def state(sample):
        with np.load(output/'states'/f'{sample:03d}.npz') as data:return {key:torch.from_numpy(data[key]).cuda() for key in data.files}
    middle=min(samples,key=lambda sample:abs((sample-samples[0])/(samples[-1]-samples[0])-manifest['frozen_control_time']))
    frozen=state(middle)
    for name in [manifest['heldout_camera'],manifest['evaluation_training_camera']]:
        folder=timeline/name;folder.mkdir(exist_ok=True)
        pose=next(r['world_to_camera'] for r in frames if r['camera_id']==name)+[[0,0,0,1]]
        camera=module.setup_camera(width,height,k,np.array(pose))
        def image(params):
            with torch.no_grad():
                rgb,_,_=module.Renderer(raster_settings=camera)(**module.params2rendervar(params))
                if name in manifest['training_cameras']:
                    index=manifest['training_cameras'].index(name)
                    rgb=torch.exp(params['cam_m'][index])[:,None,None]*rgb+params['cam_c'][index][:,None,None]
                return (rgb.clamp(0,1).permute(1,2,0).cpu().numpy()*255).round().astype(np.uint8)
        frozen_image=image(frozen)
        for sample in samples:
            current=state(sample)
            Image.fromarray(image(current)).save(folder/f'{sample:03d}-render.png')
            Image.fromarray(frozen_image).save(folder/f'{sample:03d}-frozen.png')
            with torch.no_grad():
                variables=module.params2rendervar(current);variables['colors_precomp']=current['seg_colors']
                segmentation=module.Renderer(raster_settings=camera)(**variables)[0][0].clamp(0,1)
                Image.fromarray((segmentation.cpu().numpy()*255).round().astype(np.uint8)).save(folder/f'{sample:03d}-actor.png')
            record=next(r for r in frames if r['camera_id']==name and r['sample_index']==sample)
            with Image.open(source/record['image_path']) as im:im.convert('RGB').save(folder/f'{sample:03d}-gt.png')
    print('Dynamic3DGaussians renders saved: '+str(timeline),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['train','render'])
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--initial-steps',type=int,default=2000);p.add_argument('--subsequent-steps',type=int,default=400)
    a=p.parse_args();source=a.source.resolve();output=a.output.resolve()
    if a.phase=='train':train(source,output,a.initial_steps,a.subsequent_steps)
    else:render(source,output)
