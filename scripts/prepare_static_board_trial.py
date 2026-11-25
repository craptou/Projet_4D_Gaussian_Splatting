"""Restricted single-instant trial with silhouette-volume seeds, not measured board points."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from prepare_dense_fixed_init import read_cloud,write_cloud
from static_board_geometry import project


def prepare(source,geometry,output):
    if output.exists():raise ValueError('Choose fresh dataset output')
    original=json.loads((source/'manifest.json').read_text())
    report=json.loads((geometry/'report.json').read_text())
    if not report['gate_passed']:raise ValueError('Silhouette consistency gate failed')
    if report['heldout_used_for_carving']:raise ValueError('Reserved-view leakage')
    sample=report['sample_index'];excluded=report['excluded_views']
    records=[dict(r) for r in original['frames'] if Path(r['image_path']).stem==f'{sample:03d}' and r['camera_id'] not in excluded]
    output.mkdir(parents=True)
    def stage(src,dst):
        dst.parent.mkdir(parents=True,exist_ok=True)
        try:os.link(src,dst)
        except OSError:shutil.copy2(src,dst)
        assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dst.read_bytes()).digest()
    arrays={};poses={}
    for record in records:
        name=record['camera_id'];record['time']=0.
        stage(source/record['image_path'],output/record['image_path'])
        path=f'masks/{name}.png';stage(geometry/path,output/path)
        record['evaluation_mask_path']=path
        if record['split']=='train' and name in report['carving_views']:record['foreground_mask_path']=path
        with Image.open(output/record['image_path']) as image:arrays[name]=np.array(image.convert('RGB'))
        poses[name]=np.array(record['world_to_camera'])
    hull,_=read_cloud(geometry/'strict-hull.ply')
    rng=np.random.default_rng(24)
    selected=rng.choice(len(hull),min(3000,len(hull)),replace=False)
    board=hull[selected]
    colors=[]
    for name in report['carving_views']:
        uv,z=project(board,poses[name],original['intrinsics'])
        xy=np.rint(uv).astype(int);x=xy[:,0].clip(0,562);y=xy[:,1].clip(0,1217)
        colors.append(arrays[name][y,x])
    rgb=np.median(np.stack(colors),axis=0).astype(np.uint8)
    background,bg_rgb=read_cloud(source/'points3D_multipleview.ply')
    xyz=np.concatenate([background,board]);rgb=np.concatenate([bg_rgb,rgb])
    write_cloud(output/'points3D_multipleview.ply',xyz,rgb)
    manifest=dict(original,frames=records,static_scene=True,
        training_cameras=[r['camera_id'] for r in records if r['split']=='train'],
        initialization_points=len(xyz),initialization='Original observed background points plus sampled training-silhouette visual-hull voxels; board samples are synthetic volume hypotheses, not measured surface points',
        foreground_loss=dict(weight=.1,cameras=report['carving_views'],masked_training_images=len(report['carving_views']),
            rule='Full-image L1 + 0.1 * candidate-foreground mean L1 on 13 masked training views; view11 remains full-image only'),
        physical_time_span_seconds=0.,normalized_time_rule='All images use time zero; renderer forced to undeformed coarse branch',
        excluded_views=excluded,carving_views=report['carving_views'],sample_index=sample,
        limitations='Restricted 14-view exploratory static trial, not an ablation of the prior dynamic run. Excluded cameras remain unresolved. Candidate masks and visual hull are approximate. No motion or rotation measurement.')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    preparation=dict(sample_index=sample,seconds_before_score=report['seconds_before_score'],train_images=len(manifest['training_cameras']),test_images=sum(r['split']=='test' for r in records),
        background_points=len(background),board_seed_points=len(board),board_seed_method='Random seed24, sample up to3000 strict visual-hull voxels without replacement; median sampled training colors',
        source_manifest_sha256=hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),
        heldout_used_for_seeds=False,excluded_views=excluded,masked_training_views=report['carving_views'],
        compared_with_prior_run='Time, view subset, initialization and foreground loss all change; feasibility trial, not a causal ablation')
    (output/'preparation.json').write_text(json.dumps(preparation,indent=2)+'\n')
    sheet=Image.new('RGB',(900,4*456),'white');draw=ImageDraw.Draw(sheet)
    projection_metrics={}
    for row,name in enumerate(['view03','view04','view19',manifest['heldout_camera']]):
        uv,z=project(hull,poses[name],original['intrinsics']);xy=np.rint(uv).astype(int)
        inside=(z>0)&(xy[:,0]>=0)&(xy[:,0]<563)&(xy[:,1]>=0)&(xy[:,1]<1218)
        silhouette=np.zeros((1218,563),np.uint8);silhouette[xy[inside,1],xy[inside,0]]=255
        silhouette=np.array(Image.fromarray(silhouette).filter(ImageFilter.MaxFilter(3)))>0
        with Image.open(output/f'masks/{name}.png') as image:mask=np.array(image)>0
        iou=float((silhouette&mask).sum()/(silhouette|mask).sum())
        projection_metrics[name]=dict(candidate_mask_iou=iou,projected_pixels=int(silhouette.sum()),candidate_mask_pixels=int(mask.sum()),used_for_carving=name in report['carving_views'])
        overlay=arrays[name].copy();overlay[silhouette]=(overlay[silhouette]*.4+[0,100,150]).clip(0,255).astype(np.uint8)
        binary=np.repeat((silhouette*255).astype(np.uint8)[:,:,None],3,axis=2)
        for col,(label,array) in enumerate([('Recording',arrays[name]),('Hull overlay',overlay),('Projected hull',binary)]):
            tile=Image.fromarray(array).crop((0,400,563,1200)).resize((300,426));sheet.paste(tile,(col*300,row*456+30))
            draw.text((col*300+4,row*456+8),f'{name}: {label}',fill='black')
    sheet.save(output/'hull-projection-review.jpg',quality=93)
    (output/'hull-projection.json').write_text(json.dumps(projection_metrics,indent=2)+'\n')
    print(json.dumps(preparation,indent=2),flush=True);print(json.dumps(projection_metrics,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-clean-pilot'))
    p.add_argument('--geometry',type=Path,default=Path('outputs/static-board-core'))
    p.add_argument('--output',type=Path,default=Path('data/processed/true-skate-static-board'))
    a=p.parse_args();prepare(a.source,a.geometry,a.output)
