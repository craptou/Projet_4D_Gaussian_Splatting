"""Compare approximate deck envelopes with automatic masks and the unchanged initial hull."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageOps
from prepare_dense_fixed_init import read_cloud
from static_board_geometry import project


def polygon_mask(points,size):
    points=np.asarray(points,dtype=float)
    if points.ndim!=2 or points.shape[1]!=2 or len(points)<3 or not np.isfinite(points).all():raise ValueError('Invalid polygon')
    if np.any(points<0) or np.any(points>=np.array(size)):raise ValueError('Polygon outside image')
    mask=Image.new('L',tuple(size));ImageDraw.Draw(mask).polygon([tuple(p) for p in points],fill=255)
    return np.array(mask)>0


def iou(a,b):
    union=np.count_nonzero(a|b)
    if union==0:raise ValueError('Empty union')
    return float(np.count_nonzero(a&b)/union)


def audit(source,hull_path,annotations,run,output):
    output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((source/'manifest.json').read_text());labels=json.loads(annotations.read_text())
    if labels['image_resolution']!=manifest['image_resolution']:raise ValueError('Annotation coordinates differ from image resolution')
    hull,_=read_cloud(hull_path);records={r['camera_id']:r for r in manifest['frames']}
    report=dict(annotation_sha256=hashlib.sha256(annotations.read_bytes()).hexdigest(),provenance=labels['provenance'],
        source_image_sha256={},views={},limitations='Approximate deck-envelope evaluation; excludes wheel protrusions and fills occlusions. Automatic masks target RGB change, not the same semantic class. No retraining, camera modification, or hull modification.')
    sheet=Image.new('RGB',(1200,4*310),'white');draw=ImageDraw.Draw(sheet)
    for row,(name,points) in enumerate(labels['polygons'].items()):
        record=records[name];size=manifest['image_resolution']
        manual=polygon_mask(points,size)
        with Image.open(source/record['evaluation_mask_path']) as image:automatic=np.array(image)>0
        uv,z=project(hull,np.array(record['world_to_camera']),manifest['intrinsics']);xy=np.rint(uv).astype(int)
        valid=(z>0)&(xy[:,0]>=0)&(xy[:,0]<size[0])&(xy[:,1]>=0)&(xy[:,1]<size[1])
        projection=np.zeros(manual.shape,np.uint8);projection[xy[valid,1],xy[valid,0]]=255
        projection=np.array(Image.fromarray(projection).filter(ImageFilter.MaxFilter(3)))>0
        with Image.open(source/record['image_path']) as image:target=np.array(image.convert('RGB'))
        report['source_image_sha256'][name]=hashlib.sha256((source/record['image_path']).read_bytes()).hexdigest()
        sensitivities={}
        for label,method in [('erode2',ImageFilter.MinFilter(5)),('dilate2',ImageFilter.MaxFilter(5))]:
            modified=np.array(Image.fromarray(manual.astype(np.uint8)*255).filter(method))>0
            sensitivities[label]=iou(projection,modified)
        group=('train-' if record['split']=='train' else 'test-')+name
        with Image.open(run/'renders-2000'/group/'renders/000.png') as image:pred=np.array(image.convert('RGB'))
        errors=(pred.astype(np.float32)-target.astype(np.float32))/255
        report['views'][name]=dict(split=record['split'],approximate_deck_pixels=int(manual.sum()),automatic_pixels=int(automatic.sum()),
            automatic_coverage_of_deck=float((automatic&manual).sum()/manual.sum()),
            hull_vs_automatic_iou=iou(projection,automatic),hull_vs_approximate_deck_iou=iou(projection,manual),
            two_pixel_annotation_sensitivity=sensitivities,static_render_approximate_deck_psnr_db=float(-10*np.log10(max(float((errors[manual]**2).mean()),1e-12))))
        ys,xs=np.where(manual);box=(max(0,int(xs.min())-15),max(0,int(ys.min())-15),min(size[0],int(xs.max())+16),min(size[1],int(ys.max())+16))
        overlays=[]
        for label,mask,color in [('Approximate deck outline',manual,[0,150,0]),('Old automatic mask',automatic,[150,80,0]),('Unchanged initial hull',projection,[0,100,150])]:
            array=target.copy();array[mask]=(array[mask]*.4+color).clip(0,255).astype(np.uint8)
            overlays.append((label,array))
        for col,(label,array) in enumerate([('Recording',target)]+overlays):
            tile=ImageOps.contain(Image.fromarray(array).crop(box),(290,260))
            sheet.paste(tile,(col*300+(300-tile.width)//2,row*310+35+(260-tile.height)//2))
            draw.text((col*300+4,row*310+8),f'{name}: {label}',fill='black')
        Image.fromarray(manual.astype(np.uint8)*255).save(output/(name+'-deck.png'))
    sheet.save(output/'mask-comparison.jpg',quality=95)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-static-board'))
    p.add_argument('--hull',type=Path,default=Path('outputs/static-board-core/strict-hull.ply'))
    p.add_argument('--annotations',type=Path,default=Path('data/annotations/static-deck-2026-11-24.json'))
    p.add_argument('--run',type=Path,default=Path('outputs/static-board-pilot/gpu'))
    p.add_argument('--output',type=Path,default=Path('outputs/deck-mask-audit'))
    a=p.parse_args();audit(a.source,a.hull,a.annotations,a.run,a.output)
