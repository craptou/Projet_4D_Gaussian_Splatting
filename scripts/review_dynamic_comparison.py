"""Evaluate common saved PNGs and verify equal inputs, without equating model/loss/budget choices."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageOps
from audit_deck_masks import polygon_mask
from prepare_dense_fixed_init import read_cloud


def psnr(pred,target,mask=None):
    error=(pred.astype(np.float64)-target.astype(np.float64))/255
    if mask is not None:
        if not mask.any():return None
        error=error[mask]
    return float(-10*np.log10(max(float((error**2).mean()),1e-12)))


def overlap(pred,target):
    union=(pred|target).sum()
    return float((pred&target).sum()/union) if union else None


def evaluate(folder,source,name,polygons):
    samples=list(range(3,13))
    def rgb(path):
        with Image.open(path) as image:return np.array(image.convert('RGB'))
    targets=np.stack([rgb(folder/f'{i:03d}-gt.png') for i in samples])
    renders=np.stack([rgb(folder/f'{i:03d}-render.png') for i in samples])
    frozen=np.stack([rgb(folder/f'{i:03d}-frozen.png') for i in samples])
    if not np.all(frozen==frozen[0]):raise ValueError('Frozen-time control changes')
    for i,sample in enumerate(samples):
        if not np.array_equal(targets[i],rgb(source/f'images/{name}/{sample:03d}.png')):raise ValueError('Incorrect evaluation target')
    change=np.ptp(targets.astype(np.int16),axis=0).max(2)>45
    def score(images):
        return dict(mean_full_psnr_db=float(np.mean([psnr(a,b) for a,b in zip(images,targets)])),
            change_union_psnr_db=float(np.mean([psnr(a,b,change) for a,b in zip(images,targets)])))
    def variation(images):return float(np.abs(np.diff(images.astype(np.float64),axis=0))[:,~change].mean()/255)
    result=dict(dynamic=score(renders),frozen=score(frozen),background_interframe_mae=variation(renders),
        target_background_interframe_mae=variation(targets),change_union_pixels=int(change.sum()),deck={},actor_mask_proxy={})
    for sample in [3,8,12]:
        index=sample-3;mask=polygon_mask(polygons[sample][name],[563,1218])
        result['deck'][str(sample)]=psnr(renders[index],targets[index],mask)
    for threshold in [.1,.5]:
        values=[]
        for sample in samples:
            with Image.open(folder/f'{sample:03d}-actor.png') as image:pred=np.array(image.convert('L'))/255>threshold
            with Image.open(source/f'masks/{name}/{sample:03d}.png') as image:target=np.array(image.convert('L'))>0
            values.append(dict(sample=sample,iou=overlap(pred,target),predicted_pixels=int(pred.sum()),candidate_pixels=int(target.sum())))
        result['actor_mask_proxy'][str(threshold)]=dict(mean_iou=float(np.mean([r['iou'] for r in values])),frames=values)
    return result


def review(output):
    output.mkdir(parents=True,exist_ok=True)
    source=Path('data/processed/true-skate-dense-comparison')
    manifest=json.loads((source/'manifest.json').read_text());preparation=json.loads((source/'dense-preparation.json').read_text())
    preparation['hashes']={path.replace('\\','/'):digest for path,digest in preparation['hashes'].items()}
    for path,digest in preparation['hashes'].items():
        if hashlib.sha256((source/path).read_bytes()).hexdigest()!=digest:raise ValueError('Source input mutated')
    four=Path('outputs/dense-persistent');dynamic=Path('outputs/dynamic-comparison/gpu')
    four_report=json.loads((four/'gpu/report.json').read_text());dynamic_report=json.loads((dynamic/'report.json').read_text())
    if dynamic_report['input_manifest_sha256']!=hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest():raise ValueError('Different source manifest')
    metadata=json.loads((dynamic/'work/data/replay/train_meta.json').read_text())
    expected=[f'{name}/{sample:03d}.png' for sample in manifest['sample_indices'] for name in manifest['training_cameras']]
    if [name for group in metadata['fn'] for name in group]!=expected:raise ValueError('Dynamic camera/time optimization set differs')
    if four_report['loader']['training_samples']!=len(expected):raise ValueError('4DGS optimization count differs')
    f,cx,cy=manifest['intrinsics'];intrinsics=np.array([[f,0,cx],[0,f,cy],[0,0,1]])
    records={(r['camera_id'],r['sample_index']):r for r in manifest['frames']}
    for t,sample in enumerate(manifest['sample_indices']):
        for c,name in enumerate(manifest['training_cameras']):
            record=records[name,sample]
            if not np.array_equal(metadata['k'][t][c],intrinsics):raise ValueError('Different camera intrinsics')
            if not np.array_equal(metadata['w2c'][t][c],record['world_to_camera']+[[0,0,0,1]]):raise ValueError('Different camera poses')
    for filename in expected:
        if hashlib.sha256((dynamic/'work/data/replay/ims'/filename).read_bytes()).hexdigest()!=preparation['hashes']['images/'+filename]:raise ValueError('Different optimization RGB pixels')
        with Image.open(dynamic/'work/data/replay/seg'/filename) as image:actual=np.array(image)
        with Image.open(source/'masks'/filename) as image:wanted=(np.array(image)>0).astype(np.uint8)
        if not np.array_equal(actual,wanted):raise ValueError('Different segmentation target or wrong 0/1 encoding')
    xyz,rgb=read_cloud(source/'points3D_multipleview.ply')
    cloud=np.load(dynamic/'work/data/replay/init_pt_cld.npz')['data'];start=preparation['initial_background_points']
    if not np.array_equal(cloud[:,:3],xyz) or not np.array_equal(cloud[:,3:6],rgb.astype(np.float32)/255):raise ValueError('Different initialization')
    if not np.array_equal(cloud[:,6],np.arange(len(cloud))>=start):raise ValueError('Incorrect seed ancestry')
    labels=json.loads(Path('data/annotations/multi-instant-deck-2026-11-24.json').read_text())
    reference=json.loads(Path(labels['sample8_annotations']).read_text())
    polygons={3:labels['samples']['3'],8:reference['polygons'],12:labels['samples']['12']}
    paths={'four_d':four/'timeline-6000','dynamic_3d':dynamic/'timeline'}
    metrics={label:{name:evaluate(folder/name,source,name,polygons) for name in ['view20','view19']} for label,folder in paths.items()}
    for name in ['view20','view19']:
        frames=[];sheet=Image.new('RGB',(900,810),'white');draw=ImageDraw.Draw(sheet)
        for sample in range(3,13):
            frame=Image.new('RGB',(900,456),'white');fd=ImageDraw.Draw(frame)
            images=[('Recording',paths['four_d']/name/f'{sample:03d}-gt.png'),
                ('4DGS persistent',paths['four_d']/name/f'{sample:03d}-render.png'),
                ('Dynamic3DGS adapted',paths['dynamic_3d']/name/f'{sample:03d}-render.png')]
            for col,(label,path) in enumerate(images):
                with Image.open(path) as image:
                    frame.paste(image.crop((0,400,563,1200)).resize((300,426)),(col*300,30))
                    if sample in polygons:
                        ys,xs=np.where(polygon_mask(polygons[sample][name],[563,1218]));row=[3,8,12].index(sample)
                        tile=ImageOps.contain(image.crop((int(xs.min())-20,int(ys.min())-20,int(xs.max())+21,int(ys.max())+21)),(290,230))
                        sheet.paste(tile,(col*300+(300-tile.width)//2,row*270+32+(230-tile.height)//2))
                        draw.text((col*300+4,row*270+8),f'{sample}: {label}',fill='black')
                fd.text((col*300+4,8),f'{-1+sample*.05:+.2f}s / {label}',fill='black')
            frames.append(frame)
        frames[0].save(output/f'{name}-comparison.gif',save_all=True,append_images=frames[1:],duration=250,loop=0)
        sheet.save(output/f'{name}-board.jpg',quality=95)
    appearance={label:json.loads(Path(path).read_text()) for label,path in {
        'free_appearance':'outputs/joint-three-actor/timeline-6000/report.json',
        'persistent_appearance':'outputs/joint-three-persistent/timeline-6000/report.json'}.items()}
    evidence=dict(common_metrics=metrics,four_d_run=four_report,dynamic_run=dynamic_report,
        dynamic_launcher=json.loads((dynamic/'launcher.json').read_text()) if (dynamic/'launcher.json').exists() else None,
        appearance_control=appearance,appearance_run=json.loads(Path('outputs/joint-three-persistent/gpu/report.json').read_text()),
        common_preparation=preparation,verified_identical_initial_cloud=True,verified_common_optimization_images=len(expected),
        mask_encoding_verified=True,exported_camera_matrices_verified=True,exported_rgb_hashes_verified=True,
        validation_target_images_verified=40,all_ten_times_supervised=True,
        common_evaluation='Quantized RGB PNGs for both methods, same 10-time change union; PSNR floored MSE1e-12. Actor contribution thresholds0.1/0.5 compared with approximate candidate masks, not independent semantic truth.',
        limitations='Model-comparison pilot, not isolated causal ablation or published benchmark reproduction. Different losses, density schedules and iteration budgets. Repeated validation view20. No rotation/tracking ground truth.')
    (output/'report.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    print(json.dumps(metrics,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('outputs/dynamic-comparison/review'))
    a=p.parse_args()
    if os.name=='nt':
        def linux(path):return subprocess.check_output(['wsl','-d','Ubuntu-22.04','-u','root','--exec','wslpath','-a','-u',str(path)],encoding='utf-8').strip()
        subprocess.run(['wsl','-d','Ubuntu-22.04','-u','root','--exec','/opt/skate4d/venv/bin/python',
            linux(Path(__file__).resolve()),'--output',linux(a.output.resolve())],cwd=Path(__file__).resolve().parents[1],check=True)
    else:review(a.output)
