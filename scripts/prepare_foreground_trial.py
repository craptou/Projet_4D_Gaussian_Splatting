"""Keep the baseline targets/calibration; add view19-only reference-derived masks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw


def foreground_masks(targets, background):
    targets=np.asarray(targets,dtype=np.float32)/255
    background=np.asarray(background,dtype=np.float32)/255
    changing=np.ptp(targets,axis=0).max(2)>45/255
    return (np.abs(targets-background).max(3)>40/255)&changing[None]


def prepare(source,output,weight=1.0):
    if output.exists():raise ValueError("Choose a fresh output dataset")
    if not np.isfinite(weight) or weight<=0:raise ValueError("Weight must be finite and positive")
    manifest=json.loads((source/'manifest.json').read_text())
    records=[r for r in manifest['frames'] if r['camera_id']=='view19']
    if len(records)!=13 or any(r['split']!='train' for r in records):
        raise ValueError("Expected 13 training-only view19 images")
    targets=np.stack([np.array(Image.open(source/r['image_path']).convert('RGB')) for r in records])
    background=np.array(Image.open(source/'background/view19.png').convert('RGB'))
    masks=foreground_masks(targets,background)
    if any(m.sum()<20 for m in masks):raise ValueError("Insufficient candidate foreground")
    def link_or_copy(src,dst):
        try:os.link(src,dst)
        except OSError:shutil.copy2(src,dst)
    shutil.copytree(source,output,copy_function=link_or_copy)
    # Replace the linked manifest atomically rather than writing through its hard link.
    (output/'manifest.json').unlink()
    (output/'foreground').mkdir()
    sheet=Image.new('RGB',(4*280,4*420),'white');draw=ImageDraw.Draw(sheet)
    for i,(record,mask,target) in enumerate(zip(records,masks,targets)):
        path=f'foreground/view19-{i:03d}.png'
        Image.fromarray(mask.astype(np.uint8)*255).save(output/path)
        record['foreground_mask_path']=path
        overlay=target.copy()
        overlay[mask]=(overlay[mask]*.4+[0,150,0]).clip(0,255).astype(np.uint8)
        tile=Image.fromarray(overlay).crop((0,400,563,1200)).resize((280,398))
        x,y=(i%4)*280,(i//4)*420
        sheet.paste(tile,(x,y+22));draw.text((x+4,y+4),f'f{i}: {mask.sum()} candidate pixels',fill='black')
    sheet.save(output/'foreground-review.jpg',quality=92)
    manifest['foreground_loss']=dict(weight=weight,camera='view19',masked_training_images=13,
        rule='full-image mean L1 + weight * candidate-foreground mean L1 on masked training images only',
        method='Reference-derived max RGB difference >40/255 AND temporal range >45/255',
        caveat='May include shadows/appearance changes; not semantic labels. No heldout masks used.')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    source_files=[source/r['image_path'] for r in manifest['frames']]+[source/'points3D_multipleview.ply']
    hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    assert all(hashlib.sha256((output/path).read_bytes()).hexdigest()==sha for path,sha in hashes.items())
    report=dict(weight=weight,masked_training_images=13,all_targets_and_initialization_identical=True,
        source_sha256=manifest['source_sha256'],files_sha256=hashes,mask_pixels=[int(m.sum()) for m in masks],
        mean_mask_fraction=float(masks.mean()),heldout_mask_count=0,
        unchanged=['camera poses','intrinsics','images','time samples','point-cloud initialization','train/test split'])
    (output/'foreground-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='files_sha256'},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-clean-pilot'))
    p.add_argument('--output',type=Path,default=Path('data/processed/true-skate-foreground-pilot'))
    p.add_argument('--weight',type=float,default=1.0)
    a=p.parse_args();prepare(a.source,a.output,a.weight)
