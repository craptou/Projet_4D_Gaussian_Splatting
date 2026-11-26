"""Build a common ten-time dataset with complete candidate masks; reserve view20 throughout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import numpy as np
from PIL import Image,ImageDraw
from static_board_geometry import largest_component


def action_masks(images,background=None):
    targets=np.stack(images)
    if background is None:background=np.median(targets,axis=0).astype(np.uint8)
    change=np.ptp(targets.astype(np.int16),axis=0).max(2)>45
    result={}
    for sample in range(3,13):
        candidate=(np.abs(targets[sample].astype(np.int16)-background.astype(np.int16)).max(2)>40)&change
        candidate[:400]=False;candidate[1200:]=False
        result[sample]=largest_component(candidate)
    return result


def prepare(raw,canonical,output):
    if output.exists():raise ValueError('Choose fresh dataset output')
    m=json.loads((canonical/'manifest.json').read_text())
    original=json.loads((raw/'manifest.json').read_text())
    records={(r['camera_id'],int(Path(r['image_path']).stem)):r for r in original['frames']}
    geometry={r['camera_id']:r for r in m['frames']}
    candidates=[name for name in m['training_cameras'] if name!='view11']
    masks={};counts={}
    for name in candidates+[m['heldout_camera']]:
        images=[np.array(Image.open(raw/f'images/{name}/{i:03d}.png').convert('RGB')) for i in range(13)]
        bg=np.array(Image.open(raw/'background/view19.png').convert('RGB')) if name=='view19' else None
        values=action_masks(images,bg)
        # At the original three observed times retain exactly the existing masks.
        for sample in [3,8,12]:
            with Image.open(canonical/f'masks/{name}/{sample:03d}.png') as im:values[sample]=np.array(im.convert('L'))>0
        masks[name]=values;counts[name]=[int(values[i].sum()) for i in range(3,13)]
    selected=[name for name in candidates if min(counts[name])>20]
    if len(selected)<6:raise ValueError('Fewer than six training views have complete usable masks')
    if m['heldout_camera'] in selected:raise ValueError('Reserved camera leakage')
    output.mkdir(parents=True);hashes={};frames=[]
    def stage(src,dst):
        dst.parent.mkdir(parents=True,exist_ok=True)
        try:os.link(src,dst)
        except OSError:shutil.copy2(src,dst)
        hashes[dst.relative_to(output).as_posix()]=hashlib.sha256(dst.read_bytes()).hexdigest()
    for name in selected+[m['heldout_camera']]:
        for sample in range(3,13):
            record=dict(records[name,sample]);record['world_to_camera']=geometry[name]['world_to_camera']
            record.update(time=(sample-3)/9,sample_index=sample,evaluation_mask_path=f'masks/{name}/{sample:03d}.png')
            stage(raw/record['image_path'],output/record['image_path'])
            maskpath=output/record['evaluation_mask_path'];maskpath.parent.mkdir(parents=True,exist_ok=True)
            Image.fromarray(masks[name][sample].astype(np.uint8)*255).save(maskpath)
            hashes[maskpath.relative_to(output).as_posix()]=hashlib.sha256(maskpath.read_bytes()).hexdigest()
            if record['split']=='train':record['foreground_mask_path']=record['evaluation_mask_path']
            frames.append(record)
    frames.sort(key=lambda r:(r['split']!='train',r['camera_id'],r['time']))
    stage(canonical/'points3D_multipleview.ply',output/'points3D_multipleview.ply')
    stage(canonical/'preparation.json',output/'preparation.json')
    manifest=dict(m,frames=frames,training_cameras=selected,sample_indices=list(range(3,13)),normalized_times=[i/9 for i in range(10)],
        foreground_loss=dict(weight=.1,masked_training_images=len(selected)*10,rule='Full-image L1 +0.1*candidate-foreground L1 for every training image'),
        limitations='Ten supervised times; no unseen-time claim. Candidate masks, event synchronization and calibration remain approximate. Repeated validation view20, not a fresh test.',
        carving_views=[name for name in m.get('carving_views',[])],
        initialization='Unchanged historical first-instant seeds from the three-time dataset; inherited background map includes other historical training cameras.')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    report=dict(training_cameras=selected,excluded_for_missing_masks=[name for name in candidates if name not in selected],
        rgb_only_camera_excluded='view11',mask_pixels=counts,training_images=10*len(selected),validation_images=10,
        source_manifest_sha256=hashlib.sha256((canonical/'manifest.json').read_bytes()).hexdigest(),
        hashes=hashes,heldout_used_for_seeds=False,selection_uses_training_masks_only=True,
        initial_background_points=json.loads((canonical/'preparation.json').read_text())['background_points'],
        caution='Masked-camera subset and ten-time supervision differ from three-time controls. Compare both methods on this common dataset, not as a time-count-only ablation.')
    (output/'dense-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    sheet=Image.new('RGB',(10*180,len(selected)*275),'white');draw=ImageDraw.Draw(sheet)
    for row,name in enumerate(selected):
        for col,sample in enumerate(range(3,13)):
            array=np.array(Image.open(output/f'images/{name}/{sample:03d}.png').convert('RGB'))
            mask=masks[name][sample];array[mask]=(array[mask]*.4+[0,150,0]).clip(0,255).astype(np.uint8)
            sheet.paste(Image.fromarray(array).crop((0,400,563,1200)).resize((180,255)),(col*180,row*275+20))
            draw.text((col*180+3,row*275+3),f'{name}/{sample}: {mask.sum()}px',fill='black')
    sheet.save(output/'training-mask-review.jpg',quality=92)
    print(json.dumps({k:v for k,v in report.items() if k!='hashes'},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw',type=Path,default=Path('data/processed/true-skate-clean-pilot'))
    p.add_argument('--canonical',type=Path,default=Path('data/processed/true-skate-joint-three-actor'))
    p.add_argument('--output',type=Path,default=Path('data/processed/true-skate-dense-comparison'))
    a=p.parse_args();prepare(a.raw,a.canonical,a.output)
