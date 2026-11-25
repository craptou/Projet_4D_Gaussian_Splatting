"""Render-only near-clip scale control on the initial seeds and existing static model."""
import argparse
import hashlib
import json
from pathlib import Path


def check(source,run_path,config,annotations,output,factor=4.):
    import numpy as np
    from PIL import Image,ImageDraw,ImageOps
    import torch
    from fixed_pilot_engine import load
    from gaussian_renderer import render
    from static_world_scale import scaled_camera,scaled_gaussians
    from audit_deck_masks import polygon_mask
    if output.exists():raise ValueError('Choose fresh output')
    output.mkdir(parents=True)
    scene,model,pipeline,_=load(source,run_path,config,2000)
    _,initial,_,_=load(source,output/'initial-reference',config,None)
    model.active_sh_degree=2
    pipeline.compute_cov3D_python=False;pipeline.convert_SHs_python=False
    manifest=json.loads((source/'manifest.json').read_text());labels=json.loads(annotations.read_text())
    prep=json.loads((source/'preparation.json').read_text());start=prep['background_points']
    initial_seeds=torch.arange(len(initial.get_xyz),device='cuda')>=start
    records=[r for r in manifest['frames'] if r['split']=='train'];train=scene.getTrainCameras()
    cameras={r['camera_id']:train[i] for i,r in enumerate(records)};cameras['view20']=scene.getTestCameras()[0]
    paths=list((run_path/'model/point_cloud/iteration_2000').glob('*'))
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
    black=torch.zeros(3,device='cuda')
    sheet=Image.new('RGB',(1500,4*280),'white');draw=ImageDraw.Draw(sheet)
    report=dict(factor=factor,method='Uniformly scale XYZ, Gaussian standard deviations and camera translations; preserve rotations, intrinsics, opacity, SH coefficients. Undeformed renderer only.',
        checkpoint_sha256=hashes,views={},training_performed=False)
    for row,name in enumerate(['view19','view03','view04','view20']):
        camera=cameras[name];mask=polygon_mask(labels['polygons'][name],manifest['image_resolution']);bm=torch.from_numpy(mask).cuda()
        with torch.no_grad():
            old=render(camera,model,pipeline,black,stage='coarse',cam_type=scene.dataset_type)['render'].clamp(0,1)
            changed=render(scaled_camera(camera,factor),scaled_gaussians(model,factor),pipeline,black,stage='coarse',cam_type=scene.dataset_type)['render'].clamp(0,1)
            before=render(camera,scaled_gaussians(initial,1.,initial_seeds,True),pipeline,black,stage='coarse',cam_type=scene.dataset_type)['render'].clamp(0,1)
            after=render(scaled_camera(camera,factor),scaled_gaussians(initial,factor,initial_seeds,True),pipeline,black,stage='coarse',cam_type=scene.dataset_type)['render'].clamp(0,1)
        images={label:(value.permute(1,2,0).cpu().numpy()*255).round().astype(np.uint8) for label,value in [('original',old),('scaled',changed),('seed-opacity-before',before),('seed-opacity-after',after)]}
        target=(camera.original_image.permute(1,2,0).numpy()*255).round().astype(np.uint8)
        pose=np.array(next(r for r in manifest['frames'] if r['camera_id']==name)['world_to_camera'])
        board=initial.get_xyz[initial_seeds].detach().cpu().numpy();cam=board@pose[:,:3].T+pose[:,3]
        p0=cam[:,:2]/cam[:,2,None];p1=(cam[:,:2]*factor)/(cam[:,2,None]*factor)
        entry=dict(seed_depth_min_median_max=[float(cam[:,2].min()),float(np.median(cam[:,2])),float(cam[:,2].max())],
            seed_fraction_above_cuda_near_before=float((cam[:,2]>.2).mean()),seed_fraction_above_cuda_near_after=float((cam[:,2]*factor>.2).mean()),
            mathematical_projection_max_delta_pixels=float(np.max(np.abs(p0-p1))*manifest['intrinsics'][0]),
            seed_opacity_mean_before=float(before[0][bm].mean()),seed_opacity_mean_after=float(after[0][bm].mean()),
            seed_opacity_max_image_difference=float((after-before).abs().max()))
        for label,array in [('original',images['original']),('scaled',images['scaled'])]:
            error=(array.astype(np.float32)-target.astype(np.float32))/255
            entry[label+'_approximate_deck_psnr_db']=float(-10*np.log10(max(float((error[mask]**2).mean()),1e-12)))
        report['views'][name]=entry
        ys,xs=np.where(mask);box=(int(xs.min())-20,int(ys.min())-20,int(xs.max())+21,int(ys.max())+21)
        for col,(label,array) in enumerate([('Recording',target),('Original model',images['original']),('Same model, scale4',images['scaled']),
                ('Initial opacity before',images['seed-opacity-before']),('Initial opacity after',images['seed-opacity-after'])]):
            tile=ImageOps.contain(Image.fromarray(array).crop(box),(290,235));sheet.paste(tile,(col*300+(300-tile.width)//2,row*280+33+(235-tile.height)//2))
            draw.text((col*300+4,row*280+8),name+': '+label,fill='black')
        for label,array in images.items():Image.fromarray(array).save(output/f'{name}-{label}.png')
    assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
    sheet.save(output/'near-clip-comparison.jpg',quality=95)
    report['limitations']='Approximate deck envelopes for evaluation only. Scaling makes previously clipped points visible; no learned geometry has been repaired or retrained. Other calibration/timing errors remain possible.'
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-static-board'))
    p.add_argument('--run',type=Path,default=Path('outputs/static-board-pilot/gpu'))
    p.add_argument('--config',type=Path,default=Path('configs/experiments/true-skate-static-board.py'))
    p.add_argument('--annotations',type=Path,default=Path('data/annotations/static-deck-2026-11-24.json'))
    p.add_argument('--output',type=Path,default=Path('outputs/static-near-clip-audit'))
    p.add_argument('--factor',type=float,default=4.)
    a=p.parse_args();check(a.source,a.run,a.config,a.annotations,a.output,a.factor)
