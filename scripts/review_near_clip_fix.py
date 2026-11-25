"""Compare original and safe-scale static training on unchanged source pixels."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageOps
from audit_deck_masks import polygon_mask


def review(source,before,after,annotations,output):
    output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((source/'manifest.json').read_text());labels=json.loads(annotations.read_text())
    reports={label:json.loads((root/'report.json').read_text()) for label,root in [('before',before),('after',after)]}
    if reports['before']['effective_configuration']!=reports['after']['effective_configuration']:raise ValueError('Training settings differ')
    result=dict(views={},summaries={},verified_targets=0,
        scale_fix=json.loads((source/'scale-audit.json').read_text()),
        candidate_mask_warning='Old automatic region is incomplete, especially view20. Report approximate hand-traced deck regions separately; not independent ground truth.')
    for label,report in reports.items():
        train=[v['render'] for k,v in report['evaluation']['metrics'].items() if k.startswith('train-')]
        result['summaries'][label]=dict(training_14_mean_full_psnr=float(np.mean([v['mean_psnr_db'] for v in train])),
            validation=report['evaluation']['metrics']['test-view20']['render'],training_seconds=report['timing_seconds']['train'],
            gaussians=report['evaluation']['gaussian_count'])
    for record in manifest['frames']:
        name=record['camera_id'];group=('train-' if record['split']=='train' else 'test-')+name
        with Image.open(source/record['image_path']) as image:target=np.array(image.convert('RGB'))
        for root in [before,after]:
            with Image.open(root/'renders-2000'/group/'gt/000.png') as image:
                if not np.array_equal(target,np.array(image.convert('RGB'))):raise ValueError('Targets differ')
            result['verified_targets']+=1
    detail=Image.new('RGB',(900,4*270),'white');draw=ImageDraw.Draw(detail)
    scene=Image.new('RGB',(900,4*456),'white');scene_draw=ImageDraw.Draw(scene)
    for row,(name,points) in enumerate(labels['polygons'].items()):
        record=next(r for r in manifest['frames'] if r['camera_id']==name)
        group=('train-' if record['split']=='train' else 'test-')+name
        mask=polygon_mask(points,manifest['image_resolution']);ys,xs=np.where(mask)
        box=(int(xs.min())-20,int(ys.min())-20,int(xs.max())+21,int(ys.max())+21)
        images=[]
        with Image.open(source/record['image_path']) as image:target=np.array(image.convert('RGB'))
        images.append(('Recording',target));metrics=dict(split=record['split'],deck_pixels=int(mask.sum()))
        for label,root in [('Before fix',before),('Safe scale',after)]:
            with Image.open(root/'renders-2000'/group/'renders/000.png') as image:pred=np.array(image.convert('RGB'))
            images.append((label,pred));errors=(pred.astype(np.float32)-target.astype(np.float32))/255
            metrics[label]=dict(approximate_deck_psnr_db=float(-10*np.log10(max(float((errors[mask]**2).mean()),1e-12))),
                approximate_deck_mae=float(np.abs(errors[mask]).mean()))
        result['views'][name]=metrics
        for col,(label,array) in enumerate(images):
            image=Image.fromarray(array);tile=ImageOps.contain(image.crop(box),(290,230))
            detail.paste(tile,(col*300+(300-tile.width)//2,row*270+32+(230-tile.height)//2))
            draw.text((col*300+4,row*270+8),f'{name}: {label}',fill='black')
            scene.paste(image.crop((0,400,563,1200)).resize((300,426)),(col*300,row*456+30))
            scene_draw.text((col*300+4,row*456+8),f'{name}: {label}',fill='black')
    detail.save(output/'board-comparison.jpg',quality=95);scene.save(output/'scene-comparison.jpg',quality=93)
    result['limitations']='One run per setting, one nominal instant, selected14-view training subset. Same images/cameras/intrinsics/masks and config; a uniform coordinate scale changes the fixed near-clip behavior. View20 has been used for repeated validation, not a new untouched test.'
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='scale_fix'},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-static-board-safe'))
    p.add_argument('--before',type=Path,default=Path('outputs/static-board-pilot/gpu'))
    p.add_argument('--after',type=Path,default=Path('outputs/static-board-safe/gpu'))
    p.add_argument('--annotations',type=Path,default=Path('data/annotations/static-deck-2026-11-24.json'))
    p.add_argument('--output',type=Path,default=Path('outputs/near-clip-fix-review'))
    a=p.parse_args();review(a.source,a.before,a.after,a.annotations,a.output)
