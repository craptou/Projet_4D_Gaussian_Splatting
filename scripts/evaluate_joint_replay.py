"""Observed-time and unseen-time evaluation of one joint temporal checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path


def evaluation_groups(samples,observed):
    groups={'observed':[i for i,sample in enumerate(samples) if sample in observed],
        'unseen_time':[i for i,sample in enumerate(samples) if sample not in observed]}
    return {name:indices for name,indices in groups.items() if indices}


def evaluate(source,targets,run,config,output,iteration=3000):
    import numpy as np
    from PIL import Image,ImageDraw,ImageOps
    import torch
    from fixed_pilot_engine import load
    from gaussian_renderer import render
    from utils.loss_utils import ssim
    from audit_deck_masks import polygon_mask
    from prepare_dense_fixed_init import read_cloud
    if output.exists():raise ValueError('Choose fresh evaluation output')
    output.mkdir(parents=True)
    manifest=json.loads((source/'manifest.json').read_text())
    if not manifest.get('temporal_scene') or manifest.get('static_scene'):raise ValueError('Expected joint temporal scene')
    scene,model,pipeline,_=load(source,run,config,iteration);model.active_sh_degree=min(model.max_sh_degree,iteration//1000)
    prep=json.loads((source/'preparation.json').read_text())
    canonical,_=read_cloud(source/'points3D_multipleview.ply');board=canonical[prep['background_points']:]
    xyz=model.get_xyz
    near=((xyz>=torch.tensor(board.min(0)-.1,device='cuda'))&(xyz<=torch.tensor(board.max(0)+.1,device='cuda'))).all(1)
    labels=json.loads(Path('data/annotations/multi-instant-deck-2026-11-24.json').read_text())
    ref=json.loads(Path(labels['sample8_annotations']).read_text())
    polygons={3:labels['samples']['3'],8:ref['polygons'],12:labels['samples']['12']}
    train_records=[r for r in manifest['frames'] if r['split']=='train'];train=scene.getTrainCameras()
    cameras={'view20':scene.getTestCameras()[0], 'view19':train[next(i for i,r in enumerate(train_records) if r['camera_id']=='view19')]}
    first,last=manifest['sample_indices'][0],manifest['sample_indices'][-1];samples=list(range(first,last+1))
    observed=set(manifest['sample_indices']);frozen_time=manifest['frozen_control_time']
    black=torch.zeros(3,device='cuda');result=dict(iteration=iteration,observed_indices=sorted(observed),unseen_time_indices=[s for s in samples if s not in observed],
        frozen_time=frozen_time,metrics={},spatial_probe_points=int(near.sum()),
        caveat=f'{len(observed)} training times. Any intermediate evaluation-only targets are at a repeatedly inspected camera. Spatial near-clip probe and seed-ancestry renders are not semantic point tracking.')
    for name,camera in cameras.items():
        folder=output/name;folder.mkdir()
        arrays=[];predictions=[];controls=[];deck_scores={};depth_probes=[]
        camera.time=frozen_time
        with torch.no_grad():frozen=render(camera,model,pipeline,black,cam_type=scene.dataset_type)['render'].clamp(0,1).cpu()
        for sample in samples:
            time=(sample-first)/(last-first);camera.time=time
            with torch.no_grad():
                prediction=render(camera,model,pipeline,black,cam_type=scene.dataset_type)['render'].clamp(0,1).cpu()
                if manifest.get('actor_only_deformation'):
                    from fixed_actor_labels import render_labels
                    ancestry=render_labels(camera,model,pipeline)
                    Image.fromarray((ancestry.cpu().numpy()*255).round().astype(np.uint8)).save(folder/f'{sample:03d}-actor.png')
                if int(near.sum()):
                    times=torch.full((len(xyz),1),time,device='cuda')
                    moved=model._deformation(xyz,model._scaling,model._rotation,model._opacity,model.get_features,times)[0][near]
                    world_to_view=camera.world_view_transform.cuda()
                    depth=torch.cat([moved,torch.ones((len(moved),1),device='cuda')],1)@world_to_view
                    depth_probes.append(dict(sample=sample,near_cut_fraction=float((depth[:,2]<=.2).float().mean()),min_depth=float(depth[:,2].min())))
            with Image.open(targets/f'images/{name}/{sample:03d}.png') as image:array=np.array(image.convert('RGB'))
            target=torch.from_numpy(array.astype(np.float32)/255).permute(2,0,1)
            arrays.append(target);predictions.append(prediction);controls.append(frozen)
            for label,value in [('gt',target),('render',prediction),('frozen',frozen)]:
                pixels=(value.permute(1,2,0).numpy()*255).round().astype(np.uint8)
                Image.fromarray(pixels).save(folder/f'{sample:03d}-{label}.png')
            if sample in observed:
                old=run/f'renders-{iteration}'/('test-view20' if name=='view20' else 'train-view19')/'renders'/f'{sorted(observed).index(sample):03d}.png'
                with Image.open(old) as image:prior=np.array(image.convert('RGB'))
                if np.abs(prior.astype(np.int16)-(prediction.permute(1,2,0).numpy()*255).round().astype(np.int16)).max()>1:
                    raise ValueError('Repeated checkpoint render differs')
            if sample in polygons:
                mask=torch.from_numpy(polygon_mask(polygons[sample][name],manifest['image_resolution']))
                def deck(value):
                    error=(value-target)[:,mask]
                    return dict(psnr_db=float(-10*torch.log10((error**2).mean())),mae=float(error.abs().mean()))
                deck_scores[str(sample)]=dict(dynamic=deck(prediction),frozen=deck(frozen))
        target=torch.stack(arrays);pred=torch.stack(predictions);fixed=torch.stack(controls)
        change=(target.max(0).values-target.min(0).values).max(0).values>45/255
        stable=~change
        def measure(value,indices):
            a=value[indices];b=target[indices];mse=((a-b)**2).mean((1,2,3));region=((a-b)**2)[:,:,change].mean((1,2))
            return dict(mean_full_psnr_db=float((-10*torch.log10(mse)).mean()),
                mean_ssim=float(np.mean([ssim(x[None],y[None]).item() for x,y in zip(a,b)])),
                changing_union_psnr_db=float((-10*torch.log10(region)).mean()))
        groups=evaluation_groups(samples,observed)
        result['metrics'][name]=dict(groups={g:dict(dynamic=measure(pred,indices),frozen=measure(fixed,indices)) for g,indices in groups.items()},
            deck=deck_scores,changing_union_pixels=int(change.sum()),
            target_stable_background_interframe_mae=float((target[1:]-target[:-1]).abs()[:,:,stable].mean()),
            predicted_stable_background_interframe_mae=float((pred[1:]-pred[:-1]).abs()[:,:,stable].mean()),
            near_clip_spatial_probe=depth_probes)
        frames=[];sheet=Image.new('RGB',(900,3*270),'white');draw=ImageDraw.Draw(sheet)
        for index,sample in enumerate(samples):
            frame=Image.new('RGB',(900,456),'white');fd=ImageDraw.Draw(frame)
            for col,label in enumerate(['gt','render','frozen']):
                with Image.open(folder/f'{sample:03d}-{label}.png') as image:
                    frame.paste(image.crop((0,400,563,1200)).resize((300,426)),(col*300,30))
                    if sample in polygons:
                        mask=polygon_mask(polygons[sample][name],manifest['image_resolution']);ys,xs=np.where(mask)
                        crop=image.crop((int(xs.min())-20,int(ys.min())-20,int(xs.max())+21,int(ys.max())+21))
                        tile=ImageOps.contain(crop,(290,230));row=sorted(polygons).index(sample)
                        sheet.paste(tile,(col*300+(300-tile.width)//2,row*270+32+(230-tile.height)//2))
                        draw.text((col*300+4,row*270+8),f'sample{sample}: {label}',fill='black')
                fd.text((col*300+4,8),f'{-1+sample*.05:+.2f}s / {label} / '+('observed' if sample in observed else 'unseen time'),fill='black')
            frames.append(frame)
        frames[0].save(folder/'timeline.gif',save_all=True,append_images=frames[1:],duration=250,loop=0)
        sheet.save(folder/'observed-comparison.jpg',quality=95)
    result['animation_note']=f'{len(samples)} timestamps at250ms/frame, roughly5x slower than capture time;{len(observed)} observed training times and{len(samples)-len(observed)} evaluation-only intermediate times.'
    (output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-joint-three'))
    p.add_argument('--targets',type=Path,default=Path('data/processed/true-skate-clean-pilot'))
    p.add_argument('--run',type=Path,default=Path('outputs/joint-three/gpu'))
    p.add_argument('--config',type=Path,default=Path('configs/experiments/true-skate-joint-three.py'))
    p.add_argument('--output',type=Path,default=Path('outputs/joint-three/timeline'))
    p.add_argument('--iteration',type=int,default=3000)
    a=p.parse_args();evaluate(a.source,a.targets,a.run,a.config,a.output,a.iteration)
