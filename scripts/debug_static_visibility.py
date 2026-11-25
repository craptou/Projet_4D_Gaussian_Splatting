"""Render-only diagnostics of the existing static checkpoint; no fitting or model writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace


def run(source,run_path,config,hull_path,annotations,output):
    os.environ.setdefault('OMP_NUM_THREADS','4')
    import numpy as np
    from PIL import Image,ImageDraw,ImageOps
    import torch
    from fixed_pilot_engine import load
    from gaussian_renderer import render
    from prepare_dense_fixed_init import read_cloud
    from audit_deck_masks import polygon_mask
    if output.exists():raise ValueError('Choose fresh output')
    output.mkdir(parents=True)
    checkpoint=run_path/'model/point_cloud/iteration_2000/point_cloud.ply'
    fingerprint=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    scene,model,pipeline,_=load(source,run_path,config,2000)
    _,initial,_,_=load(source,output/'initial-reference',config,None)
    pipeline.compute_cov3D_python=False;pipeline.convert_SHs_python=False
    model.active_sh_degree=2
    manifest=json.loads((source/'manifest.json').read_text());labels=json.loads(annotations.read_text())
    records=[r for r in manifest['frames'] if r['split']=='train']
    train=scene.getTrainCameras()
    cameras={r['camera_id']:train[i] for i,r in enumerate(records)}
    cameras['view20']=scene.getTestCameras()[0]
    hull,_=read_cloud(hull_path)
    xyz=model.get_xyz
    lower=torch.tensor(hull.min(0)-.01,device=xyz.device);upper=torch.tensor(hull.max(0)+.01,device=xyz.device)
    near=((xyz>=lower)&(xyz<=upper)).all(1)
    preparation=json.loads((source/'preparation.json').read_text())
    background_count=preparation['background_points']
    assert len(initial.get_xyz)==background_count+preparation['board_seed_points']
    initial_board=torch.arange(len(initial.get_xyz),device=xyz.device)>=background_count
    if int(near.sum())==0:raise ValueError('Empty spatial subset')
    def proxy(select=None,tag=False,initial_model=False):
        base=initial if initial_model else model
        coords=base.get_xyz
        selected_colors=initial_board if initial_model else near
        select=torch.ones(len(coords),device=coords.device,dtype=torch.bool) if select is None else select
        features=base.get_features[select].clone()
        if tag:
            color=selected_colors[select].float()[:,None].repeat(1,3)
            features.zero_();features[:,0,:]=(color-.5)/.28209479177387814
        return SimpleNamespace(get_xyz=coords[select],_opacity=base._opacity[select],get_features=features,
            _scaling=base._scaling[select],_rotation=base._rotation[select],_deformation_table=base._deformation_table[select],
            active_sh_degree=0 if tag else base.active_sh_degree,max_sh_degree=base.max_sh_degree,
            scaling_activation=base.scaling_activation,rotation_activation=base.rotation_activation,opacity_activation=base.opacity_activation)
    black=torch.zeros(3,device='cuda')
    result=dict(checkpoint_sha256=fingerprint,subset_points=int(near.sum()),total_points=len(xyz),
        subset_rule='Trained point centers inside initial hull axis-aligned bounds expanded0.01 normalized units; spatial diagnostic, not semantic labels or tracked seed identities',views={})
    result['initial_board_seed_count']=int(initial_board.sum())
    sheet=Image.new('RGB',(1800,3*280),'white');draw=ImageDraw.Draw(sheet)
    for row,name in enumerate(['view19','view03','view20']):
        camera=cameras[name]
        mask=polygon_mask(labels['polygons'][name],manifest['image_resolution'])
        with torch.no_grad():
            model.active_sh_degree=2
            full=render(camera,model,pipeline,black,stage='coarse',cam_type=scene.dataset_type)['render'].clamp(0,1)
            model.active_sh_degree=0
            dc=render(camera,model,pipeline,black,stage='coarse',cam_type=scene.dataset_type)['render'].clamp(0,1)
            model.active_sh_degree=2
            only=render(camera,proxy(near,True),pipeline,black,stage='coarse',cam_type=scene.dataset_type)['render'].clamp(0,1)
            contribution=render(camera,proxy(tag=True),pipeline,black,stage='coarse',cam_type=scene.dataset_type)['render'].clamp(0,1)
            initial_alpha=render(camera,proxy(initial_board,True,True),pipeline,black,stage='coarse',cam_type=scene.dataset_type)['render'].clamp(0,1)
        arrays={label:(value.permute(1,2,0).cpu().numpy()*255).round().astype(np.uint8)
                for label,value in [('full',full),('dc-only',dc),('subset-opacity',only),('subset-contribution',contribution),('initial-seed-opacity',initial_alpha)]}
        reference=run_path/'renders-2000'/('test-view20' if name=='view20' else 'train-'+name)/'renders/000.png'
        with Image.open(reference) as image:prior=np.array(image.convert('RGB'))
        max_difference=int(np.abs(arrays['full'].astype(np.int16)-prior.astype(np.int16)).max())
        if max_difference>1:raise ValueError('Checkpoint render differs from prior evidence')
        bool_mask=torch.from_numpy(mask).to(device=only.device)
        mean_only=float(only[0][bool_mask].mean());mean_contribution=float(contribution[0][bool_mask].mean())
        target=(camera.original_image.permute(1,2,0).numpy()*255).round().astype(np.uint8)
        result['views'][name]=dict(original_render_max_difference_levels=max_difference,
            initial_board_seed_opacity_mean=float(initial_alpha[0][bool_mask].mean()),
            subset_opacity_without_other_points_mean=mean_only,subset_contribution_in_full_scene_mean=mean_contribution,
            relative_visibility_ratio=mean_contribution/max(mean_only,1e-8),
            full_deck_mae=float(np.abs(arrays['full'].astype(np.float32)-target)[mask].mean()/255),
            dc_only_deck_mae=float(np.abs(arrays['dc-only'].astype(np.float32)-target)[mask].mean()/255))
        ys,xs=np.where(mask);box=(int(xs.min())-20,int(ys.min())-20,int(xs.max())+21,int(ys.max())+21)
        for col,(label,array) in enumerate([('Recording',target),('Original SH2',arrays['full']),('Initial seed opacity',arrays['initial-seed-opacity']),('Same model SH0',arrays['dc-only']),
                ('Subset opacity alone',arrays['subset-opacity']),('Subset in full scene',arrays['subset-contribution'])]):
            tile=ImageOps.contain(Image.fromarray(array).crop(box),(290,235))
            sheet.paste(tile,(col*300+(300-tile.width)//2,row*280+32+(235-tile.height)//2))
            draw.text((col*300+4,row*280+8),f'{name}: {label}',fill='black')
        for label,array in arrays.items():Image.fromarray(array).save(output/f'{name}-{label}.png')
    sheet.save(output/'visibility-comparison.jpg',quality=95)
    assert fingerprint==hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    result['limitations']='Spatial crop is not an object segmentation. Contribution image tags selected Gaussians white and all others black, preserving geometry/opacity. Difference from subset-only opacity isolates attenuation by excluded Gaussians for this crop. No model edits saved; no training.'
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-static-board'))
    p.add_argument('--run',type=Path,default=Path('outputs/static-board-pilot/gpu'))
    p.add_argument('--config',type=Path,default=Path('configs/experiments/true-skate-static-board.py'))
    p.add_argument('--hull',type=Path,default=Path('outputs/static-board-core/strict-hull.ply'))
    p.add_argument('--annotations',type=Path,default=Path('data/annotations/static-deck-2026-11-24.json'))
    p.add_argument('--output',type=Path,default=Path('outputs/static-visibility-audit'))
    a=p.parse_args();run(a.source,a.run,a.config,a.hull,a.annotations,a.output)
