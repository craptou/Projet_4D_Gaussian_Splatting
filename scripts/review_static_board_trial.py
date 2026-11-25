"""Review two restricted static fits on identical targets; export compact evidence."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageOps
from prepare_dense_fixed_init import read_cloud


def saved_positions(path):
    with path.open('rb') as handle:
        header=[]
        while True:
            line=handle.readline().decode('ascii').strip();header.append(line)
            if line=='end_header':break
            if len(header)>200:raise ValueError('Invalid model PLY header')
        properties=[line.split() for line in header if line.startswith('property ')]
        if any(row[1]!='float' for row in properties):raise ValueError('Expected float model PLY')
        data=np.frombuffer(handle.read(),dtype=np.dtype([(row[2],'<f4') for row in properties]))
    return np.column_stack([data[k] for k in ['x','y','z']])


def review(source,free,fixed,output):
    output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((source/'manifest.json').read_text())
    runs={name:json.loads((path/'report.json').read_text()) for name,path in [('static_fit',free),('fixed_geometry',fixed)]}
    summaries={};verified=0
    for name,run in runs.items():
        training=[v['render'] for k,v in run['evaluation']['metrics'].items() if k.startswith('train-')]
        summaries[name]=dict(training_14_mean={k:float(np.mean([v[k] for v in training])) for k in training[0]},
            reserved=run['evaluation']['metrics']['test-view20']['render'],gaussians=run['evaluation']['gaussian_count'],
            training_seconds=run['timing_seconds']['train'])
    roi={}
    for record in manifest['frames']:
        name=record['camera_id'];group=('train-' if record['split']=='train' else 'test-')+name
        with Image.open(source/record['image_path']) as image:target=np.array(image.convert('RGB'))
        with Image.open(source/record['evaluation_mask_path']) as image:mask=np.array(image)>0
        ys,xs=np.where(mask);box=(max(0,int(xs.min())-20),max(0,int(ys.min())-20),min(563,int(xs.max())+21),min(1218,int(ys.max())+21))
        roi[name]=dict(box=list(box),split=record['split'])
        left,top,right,bottom=box
        for label,path in [('static_fit',free),('fixed_geometry',fixed)]:
            folder=path/'renders-2000'/group
            with Image.open(folder/'gt/000.png') as image:
                if not np.array_equal(target,np.array(image.convert('RGB'))):raise ValueError('Targets changed')
            verified+=1
            with Image.open(folder/'renders/000.png') as image:prediction=np.array(image.convert('RGB'))
            difference=(prediction[top:bottom,left:right].astype(np.float32)-target[top:bottom,left:right].astype(np.float32))/255
            roi[name][label+'_psnr_db']=float(-10*np.log10(max(float(np.mean(difference**2)),1e-12)))
    init,_=read_cloud(source/'points3D_multipleview.ply')
    fitted=saved_positions(fixed/'model/point_cloud/iteration_2000/point_cloud.ply')
    if not np.array_equal(init,fitted):raise ValueError('Fixed-geometry positions changed')
    report=dict(summaries=summaries,roi=roi,verified_target_pairs=verified,fixed_positions_identical_to_initialization=True,
        initial_points=len(init),preparation=json.loads((source/'preparation.json').read_text()),
        static_runs=runs,caution='Restricted single instant. Candidate masks are approximate. Training-region scores measure fit; view20 is validation, not a new untouched test. No direct causal comparison with prior dynamic runs.')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    examples=[('view19','train-view19'),('view03','train-view03'),('view20','test-view20')]
    scene=Image.new('RGB',(900,3*456),'white');zoom=Image.new('RGB',(900,3*270),'white')
    scene_draw=ImageDraw.Draw(scene);zoom_draw=ImageDraw.Draw(zoom)
    for row,(name,group) in enumerate(examples):
        targets=[('Recording',free/'renders-2000'/group/'gt/000.png'),('Static fit',free/'renders-2000'/group/'renders/000.png'),
            ('Fixed geometry',fixed/'renders-2000'/group/'renders/000.png')]
        for col,(label,path) in enumerate(targets):
            with Image.open(path) as image:
                scene.paste(image.crop((0,400,563,1200)).resize((300,426)),(col*300,row*456+30))
                tile=ImageOps.contain(image.crop(tuple(roi[name]['box'])),(290,230))
                zoom.paste(tile,(col*300+(300-tile.width)//2,row*270+30+(230-tile.height)//2))
            text=f'{group}: {label}'
            scene_draw.text((col*300+4,row*456+8),text,fill='black');zoom_draw.text((col*300+4,row*270+8),text,fill='black')
    scene.save(output/'scene-comparison.jpg',quality=93);zoom.save(output/'board-comparison.jpg',quality=95)
    print(json.dumps(summaries,indent=2),flush=True)
    print('Exact targets verified:',verified,'; fixed XYZ identical:',len(init),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-static-board'))
    p.add_argument('--free',type=Path,default=Path('outputs/static-board-pilot/gpu'))
    p.add_argument('--fixed',type=Path,default=Path('outputs/static-board-fixed/gpu'))
    p.add_argument('--output',type=Path,default=Path('outputs/static-board-review'))
    a=p.parse_args();review(a.source,a.free,a.fixed,a.output)
