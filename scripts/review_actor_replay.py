"""Compare equal-budget global and actor-only deformation with identical input targets."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageOps
from audit_deck_masks import polygon_mask


def review(output):
    output.mkdir(parents=True,exist_ok=True)
    sources=[Path('data/processed/true-skate-joint-three'),Path('data/processed/true-skate-joint-three-actor')]
    manifests=[json.loads((p/'manifest.json').read_text()) for p in sources]
    actor=manifests[1].copy()
    if actor.pop('actor_only_deformation') is not True:raise ValueError('Actor routing not enabled')
    actor.pop('deformation_partition')
    if actor!=manifests[0]:raise ValueError('Dataset change beyond routing metadata')
    hashes=json.loads((sources[1]/'actor-preparation.json').read_text())['data_hashes']
    for path,digest in hashes.items():
        for source in sources:
            if hashlib.sha256((source/path).read_bytes()).hexdigest()!=digest:raise ValueError('Input mutation')
    runs=[Path('outputs/joint-three-duration'),Path('outputs/joint-three-actor')]
    training=[json.loads((run/'gpu/report.json').read_text()) for run in runs]
    if training[0]['effective_configuration']!=training[1]['effective_configuration']:raise ValueError('Training settings differ')
    timelines=[json.loads((run/'timeline-6000/report.json').read_text()) for run in runs]
    labels=json.loads(Path('data/annotations/multi-instant-deck-2026-11-24.json').read_text())
    reference=json.loads(Path(labels['sample8_annotations']).read_text())
    polygons={3:labels['samples']['3'],8:reference['polygons'],12:labels['samples']['12']}
    comparisons=0
    for name in ['view20','view19']:
        frames=[];sheet=Image.new('RGB',(900,810),'white');draw=ImageDraw.Draw(sheet)
        fixed_pixels=None
        for sample in range(3,13):
            folders=[run/f'timeline-6000/{name}' for run in runs]
            arrays=[]
            for folder in folders:
                with Image.open(folder/f'{sample:03d}-gt.png') as im:arrays.append(np.array(im.convert('RGB')))
            with Image.open(Path('data/processed/true-skate-clean-pilot')/f'images/{name}/{sample:03d}.png') as im:original=np.array(im.convert('RGB'))
            if not all(np.array_equal(original,a) for a in arrays):raise ValueError('Evaluation target mismatch')
            comparisons+=2
            with Image.open(folders[1]/f'{sample:03d}-frozen.png') as im:frozen=np.array(im)
            if fixed_pixels is None:fixed_pixels=frozen
            if not np.array_equal(fixed_pixels,frozen):raise ValueError('Frozen control moves')
            paths=[('Recording',folders[0]/f'{sample:03d}-gt.png'),
                ('Global deformation',folders[0]/f'{sample:03d}-render.png'),
                ('Actor-only deformation',folders[1]/f'{sample:03d}-render.png')]
            frame=Image.new('RGB',(900,456),'white');fd=ImageDraw.Draw(frame)
            for col,(label,path) in enumerate(paths):
                with Image.open(path) as im:
                    frame.paste(im.crop((0,400,563,1200)).resize((300,426)),(col*300,30))
                    if sample in polygons:
                        ys,xs=np.where(polygon_mask(polygons[sample][name],[563,1218]))
                        tile=ImageOps.contain(im.crop((int(xs.min())-20,int(ys.min())-20,int(xs.max())+21,int(ys.max())+21)),(290,230))
                        row=[3,8,12].index(sample)
                        sheet.paste(tile,(col*300+(300-tile.width)//2,row*270+32+(230-tile.height)//2))
                        draw.text((col*300+4,row*270+8),f'sample{sample}: {label}',fill='black')
                fd.text((col*300+4,8),f'{-1+sample*.05:+.2f}s / {label}',fill='black')
            frames.append(frame)
        frames[0].save(output/f'{name}-comparison.gif',save_all=True,append_images=frames[1:],duration=250,loop=0)
        sheet.save(output/f'{name}-board.jpg',quality=95)
    evidence=dict(global_run=training[0],actor_run=training[1],global_timeline=timelines[0],actor_timeline=timelines[1],
        identical_configuration=True,identical_input_file_count=len(hashes),input_hashes=hashes,
        verified_target_images=comparisons,frozen_actor_control_identical=True,
        caution='One run per treatment, CUDA trajectory not deterministic. Seed ancestry is approximate, not semantic labels or physical tracking. Same repeatedly used validation camera; no fresh test set. Seven intermediate targets excluded from optimization, not all preprocessing.')
    (output/'report.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    for label,timeline in zip(['global','actor'],timelines):
        for name in ['view20','view19']:print(label,name,json.dumps(timeline['metrics'][name]),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('outputs/joint-three-actor/review'))
    a=p.parse_args();review(a.output)
