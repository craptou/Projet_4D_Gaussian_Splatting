"""Compare three independently fitted static instants; no interpolation or tracking claims."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageOps
from audit_deck_masks import polygon_mask


def review(annotations,output):
    output.mkdir(parents=True,exist_ok=True)
    labels=json.loads(annotations.read_text())
    reference=json.loads(Path(labels['sample8_annotations']).read_text())
    polygons={3:labels['samples']['3'],8:reference['polygons'],12:labels['samples']['12']}
    sources={3:Path('data/processed/true-skate-static-sample03-safe'),8:Path('data/processed/true-skate-static-board-safe'),12:Path('data/processed/true-skate-static-sample12-safe')}
    runs={3:Path('outputs/multi-instant/sample03-gpu'),8:Path('outputs/static-board-safe/gpu'),12:Path('outputs/multi-instant/sample12-gpu')}
    summary=dict(sample_indices=[3,8,12],instants={},views={},annotation_sha256=hashlib.sha256(annotations.read_bytes()).hexdigest(),
        warning='Three separately fitted static scenes, not one dynamic model. No interpolation, physical rotations, correspondences or material tracking evaluated. Same repeated validation camera, not untouched test.')
    detail={name:Image.new('RGB',(600,3*270),'white') for name in ['view19','view20']}
    scenes={name:Image.new('RGB',(600,3*456),'white') for name in detail}
    frames={name:[] for name in detail}
    baseline_config=None;baseline_cameras=None;baseline_geometry=None
    for row,sample in enumerate([3,8,12]):
        source=sources[sample];run=runs[sample]
        manifest=json.loads((source/'manifest.json').read_text());report=json.loads((run/'report.json').read_text())
        prep=json.loads((source/'preparation.json').read_text())
        geometry=dict(intrinsics=manifest['intrinsics'],world_normalization=manifest['world_normalization'],
            camera_poses={r['camera_id']:r['world_to_camera'] for r in manifest['frames']})
        if baseline_config is None:
            baseline_config=report['effective_configuration'];baseline_cameras=manifest['training_cameras'];baseline_geometry=geometry
        if report['effective_configuration']!=baseline_config or manifest['training_cameras']!=baseline_cameras:raise ValueError('Training settings or camera set changed')
        if geometry!=baseline_geometry:raise ValueError('Camera geometry or coordinate system changed between instants')
        times={r['seconds_relative_to_score'] for r in manifest['frames']}
        if len(times)!=1:raise ValueError('Expected a single instant')
        seconds=times.pop()
        training=[v['render'] for k,v in report['evaluation']['metrics'].items() if k.startswith('train-')]
        valid=[v['candidate_foreground_region_mean_psnr_db'] for v in training if v['candidate_foreground_region_mean_psnr_db'] is not None]
        summary['instants'][str(sample)]=dict(seconds_relative_to_score=seconds,initial_points=manifest['initialization_points'],
            background_points=prep['background_points'],board_seed_points=prep['board_seed_points'],training_views=len(training),
            masks_used=manifest['foreground_loss']['masked_training_images'],training_region_metrics_available=len(valid),
            training_mean_full_psnr_db=float(np.mean([v['mean_psnr_db'] for v in training])),training_mean_available_candidate_psnr_db=float(np.mean(valid)),
            validation=report['evaluation']['metrics']['test-view20']['render'],training_seconds=report['timing_seconds']['train'],
            final_gaussians=report['evaluation']['gaussian_count'],safe_scale_factor=manifest['near_clip_guard']['factor'],
            loader=report['loader'],all_targets_verified=0)
        for record in manifest['frames']:
            name=record['camera_id'];group=('train-' if record['split']=='train' else 'test-')+name
            with Image.open(source/record['image_path']) as image:target=np.array(image.convert('RGB'))
            with Image.open(run/'renders-2000'/group/'gt/000.png') as image:
                if not np.array_equal(target,np.array(image.convert('RGB'))):raise ValueError('Source and target differ')
            summary['instants'][str(sample)]['all_targets_verified']+=1
        for name in detail:
            record=next(r for r in manifest['frames'] if r['camera_id']==name)
            group=('train-' if record['split']=='train' else 'test-')+name
            mask=polygon_mask(polygons[sample][name],manifest['image_resolution'])
            with Image.open(source/record['image_path']) as image:target=np.array(image.convert('RGB'))
            with Image.open(run/'renders-2000'/group/'renders/000.png') as image:prediction=np.array(image.convert('RGB'))
            errors=(prediction.astype(np.float32)-target.astype(np.float32))/255
            summary['views'].setdefault(name,{})[str(sample)]=dict(split=record['split'],approximate_deck_pixels=int(mask.sum()),
                approximate_deck_psnr_db=float(-10*np.log10(max(float((errors[mask]**2).mean()),1e-12))),
                approximate_deck_mae=float(np.abs(errors[mask]).mean()),source_image_sha256=hashlib.sha256((source/record['image_path']).read_bytes()).hexdigest())
            ys,xs=np.where(mask);box=(max(0,int(xs.min())-20),max(0,int(ys.min())-20),min(563,int(xs.max())+21),min(1218,int(ys.max())+21))
            frame=Image.new('RGB',(600,456),'white');d=ImageDraw.Draw(detail[name]);sd=ImageDraw.Draw(scenes[name]);fd=ImageDraw.Draw(frame)
            for col,(label,array) in enumerate([('Recording',target),('Independent static fit',prediction)]):
                image=Image.fromarray(array);tile=ImageOps.contain(image.crop(box),(290,230))
                detail[name].paste(tile,(col*300+(300-tile.width)//2,row*270+32+(230-tile.height)//2))
                scene=image.crop((0,400,563,1200)).resize((300,426))
                scenes[name].paste(scene,(col*300,row*456+30));frame.paste(scene,(col*300,30))
                caption=f'{seconds:+.2f}s / {label}'
                d.text((col*300+4,row*270+8),caption,fill='black');sd.text((col*300+4,row*456+8),caption,fill='black');fd.text((col*300+4,8),caption,fill='black')
            frames[name].append(frame)
    for name in detail:
        detail[name].save(output/(name+'-detail.jpg'),quality=95)
        scenes[name].save(output/(name+'-scene.jpg'),quality=93)
        frames[name][0].save(output/(name+'-snapshots.gif'),save_all=True,append_images=frames[name][1:],duration=800,loop=0)
    summary['gif_note']='Three snapshots held800ms each; no in-between frames or real-time motion reconstruction.'
    (output/'report.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='instants'},indent=2),flush=True)
    for sample,item in summary['instants'].items():print(sample,item['validation'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--annotations',type=Path,default=Path('data/annotations/multi-instant-deck-2026-11-24.json'))
    p.add_argument('--output',type=Path,default=Path('outputs/multi-instant/review'))
    a=p.parse_args();review(a.annotations,a.output)
