"""Compare same-run temporal checkpoints with frozen time and independent static references."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageOps
from audit_deck_masks import polygon_mask


def review(output):
    output.mkdir(parents=True,exist_ok=True)
    first=json.loads(Path('outputs/joint-three/gpu/report.json').read_text())
    duration=json.loads(Path('outputs/joint-three-duration/gpu/report.json').read_text())
    expected=json.loads(json.dumps(first['effective_configuration']));expected['OptimizationParams']['iterations']=6000
    if expected!=duration['effective_configuration']:raise ValueError('Duration control changed more than iterations')
    timelines={i:json.loads(Path(f'outputs/joint-three-duration/timeline-{i}/report.json').read_text()) for i in [3000,6000]}
    labels=json.loads(Path('data/annotations/multi-instant-deck-2026-11-24.json').read_text())
    reference=json.loads(Path(labels['sample8_annotations']).read_text())
    polygons={3:labels['samples']['3'],8:reference['polygons'],12:labels['samples']['12']}
    static_runs={3:Path('outputs/multi-instant/sample03-gpu'),8:Path('outputs/static-board-safe/gpu'),12:Path('outputs/multi-instant/sample12-gpu')}
    report=dict(initial_pilot=first,duration_run=duration,timelines=timelines,
        preparation=json.loads(Path('data/processed/true-skate-joint-three/preparation.json').read_text()),
        initialization_manifest=json.loads(Path('data/processed/true-skate-joint-three/manifest.json').read_text()),
        duration_only_config_verified=True,static_reference_deck={},
        caution='Same-run3k/6k checkpoints for duration comparison; original3k pilot is a separate run. One camera used repeatedly for validation. Static fits are reference quality, not one dynamic model or a causal ablation.')
    for name in ['view19','view20']:
        sheet=Image.new('RGB',(1200,3*270),'white');draw=ImageDraw.Draw(sheet)
        for row,sample in enumerate([3,8,12]):
            group=('test-' if name=='view20' else 'train-')+name
            mask=polygon_mask(polygons[sample][name],[563,1218]);ys,xs=np.where(mask)
            box=(int(xs.min())-20,int(ys.min())-20,int(xs.max())+21,int(ys.max())+21)
            paths=[('Recording',static_runs[sample]/'renders-2000'/group/'gt/000.png'),
                ('Independent static',static_runs[sample]/'renders-2000'/group/'renders/000.png'),
                ('Joint3k',Path(f'outputs/joint-three-duration/timeline-3000/{name}/{sample:03d}-render.png')),
                ('Joint6k',Path(f'outputs/joint-three-duration/timeline-6000/{name}/{sample:03d}-render.png'))]
            with Image.open(paths[0][1]) as image:target=np.array(image.convert('RGB'))
            for iteration in [3000,6000]:
                with Image.open(Path(f'outputs/joint-three-duration/timeline-{iteration}/{name}/{sample:03d}-gt.png')) as image:
                    if not np.array_equal(target,np.array(image.convert('RGB'))):raise ValueError('Static and temporal evaluation targets differ')
            for col,(label,path) in enumerate(paths):
                with Image.open(path) as image:
                    if label=='Independent static':
                        pred=np.array(image.convert('RGB'));errors=(pred.astype(np.float32)-target.astype(np.float32))/255
                        report['static_reference_deck'].setdefault(name,{})[str(sample)]=float(-10*np.log10(max(float((errors[mask]**2).mean()),1e-12)))
                    tile=ImageOps.contain(image.crop(box),(290,230))
                sheet.paste(tile,(col*300+(300-tile.width)//2,row*270+32+(230-tile.height)//2))
                draw.text((col*300+4,row*270+8),f'sample{sample}: {label}',fill='black')
        sheet.save(output/f'{name}-checkpoint-comparison.jpg',quality=95)
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    for iteration,timeline in timelines.items():
        print(iteration,'validation',json.dumps(timeline['metrics']['view20']['groups']),flush=True)
        print(iteration,'deck',json.dumps(timeline['metrics']['view20']['deck']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('outputs/joint-three/review'))
    a=p.parse_args();review(a.output)
