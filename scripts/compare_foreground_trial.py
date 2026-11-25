"""Compare baseline and foreground-weighted runs with identical data and budget."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw


def compare(source,weighted_source,baseline,weighted,output):
    before=json.loads((source/'manifest.json').read_text())
    after=json.loads((weighted_source/'manifest.json').read_text())
    clean=json.loads(json.dumps(after));clean.pop('foreground_loss')
    for row in clean['frames']:row.pop('foreground_mask_path',None)
    if before!=clean:raise ValueError('Baseline and weighted data differ beyond foreground masks/settings')
    preparations=json.loads((weighted_source/'foreground-preparation.json').read_text())
    for path,digest in preparations['files_sha256'].items():
        for root in [source,weighted_source]:
            if hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:
                raise ValueError('Dataset changed after preparation')
    runs={name:json.loads((root/'report.json').read_text()) for name,root in [('baseline',baseline),('weighted',weighted)]}
    if runs['baseline']['effective_configuration']!=runs['weighted']['effective_configuration']:
        raise ValueError('Training configurations differ')
    if any(run['fine_steps']!=5000 for run in runs.values()):raise ValueError('Expected matched 5000-step runs')
    output.mkdir(parents=True,exist_ok=True)
    result=dict(changed='Only add full-image L1 + 1.0 * foreground-mean L1 on view19 training samples',
        foreground_loss=after['foreground_loss'],preparation={k:v for k,v in preparations.items() if k!='files_sha256'},
        synchronization_review=dict(method='Visual review of 18 views at samples 0,6,12 plus 13 view19 masks',
            conclusion='No gross action-phase mismatch observed; no timing offsets changed',
            limitation='Does not establish frame-perfect synchronization; view20 remains validation'),
        runs=runs,evaluation_target_pairs_verified=0,
        limitation='One run per setting; shared seed 0 in upstream, CUDA determinism not guaranteed. Training-mask scores measure fit, not independent object reconstruction.')
    review=weighted.parent/'synchronization-review.json'
    if review.exists():result['synchronization_review']=json.loads(review.read_text())
    for iteration in [2000,5000]:
        for group in ['test-view20','train-view19']:
            frames=[]
            for i in range(13):
                ground_truth=[]
                for root in [baseline,weighted]:
                    with Image.open(root/f'renders-{iteration}'/group/'gt'/f'{i:03d}.png') as image:ground_truth.append(np.array(image))
                if not np.array_equal(*ground_truth):raise ValueError('Evaluation targets differ between runs')
                result['evaluation_target_pairs_verified']+=1
                canvas=Image.new('RGB',(900,456),'white');draw=ImageDraw.Draw(canvas)
                images=[('Recording',baseline/f'renders-{iteration}'/group/'gt'),
                    ('Baseline',baseline/f'renders-{iteration}'/group/'renders'),
                    ('Foreground loss',weighted/f'renders-{iteration}'/group/'renders')]
                for column,(label,folder) in enumerate(images):
                    with Image.open(folder/f'{i:03d}.png') as image:
                        canvas.paste(image.crop((0,400,563,1200)).resize((300,426)),(column*300,30))
                    draw.text((column*300+5,8),f'{group} / f{i} / {label}',fill='black')
                frames.append(canvas)
            sheet=Image.new('RGB',(900,1368),'white')
            for row,i in enumerate([0,6,12]):sheet.paste(frames[i],(0,row*456))
            sheet.save(output/f'{group}-{iteration}.jpg',quality=92)
            if iteration==5000:
                frames[0].save(output/f'{group}-comparison.gif',save_all=True,append_images=frames[1:],duration=250,loop=0)
    for name,root in [('baseline',baseline),('weighted',weighted)]:
        result[name+'_foreground']=json.loads((root.parent/'foreground-evaluation.json').read_text())
    from prepare_foreground_trial import foreground_masks
    targets=np.stack([np.array(Image.open(source/f'images/view19/{i:03d}.png').convert('RGB')) for i in range(13)])
    background=np.array(Image.open(source/'background/view19.png').convert('RGB'))
    masks=foreground_masks(targets,background)
    union=np.ptp(targets.astype(np.int16),axis=0).max(2)>45
    outside=union[None]&~masks
    spillover=dict(region='Target temporal-change union minus current-frame reference-derived candidate foreground, view19 training only',
        mean_pixels=float(outside.sum((1,2)).mean()))
    for name,root in [('baseline',baseline),('weighted',weighted)]:
        images=np.stack([np.array(Image.open(root/f'renders-5000/train-view19/renders/{i:03d}.png').convert('RGB')) for i in range(13)])
        errors=(images.astype(np.float32)-targets.astype(np.float32))/255
        spillover[name]=dict(mean_psnr_db=float(np.mean([-10*np.log10(max(float((e[m]**2).mean()),1e-12)) for e,m in zip(errors,outside)])),
            mean_absolute_error=float(np.mean([np.abs(e[m]).mean() for e,m in zip(errors,outside)])))
    result['spillover_diagnostic']=spillover
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Matched target pairs:',result['evaluation_target_pairs_verified'])
    for name,run in runs.items():
        for group,metrics in run['evaluation']['metrics'].items():
            print(name,group,json.dumps(metrics['render']),flush=True)
        print(name,'foreground',result[name+'_foreground']['checkpoints']['5000']['renders'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-clean-pilot'))
    p.add_argument('--weighted-source',type=Path,default=Path('data/processed/true-skate-foreground-pilot'))
    p.add_argument('--baseline',type=Path,default=Path('outputs/clean-replay-pipeline/gpu'))
    p.add_argument('--weighted',type=Path,default=Path('outputs/foreground-pilot/gpu'))
    p.add_argument('--output',type=Path,default=Path('outputs/foreground-pilot/comparison'))
    a=p.parse_args();compare(a.source,a.weighted_source,a.baseline,a.weighted,a.output)
