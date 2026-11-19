"""Retry only failed localizations with reviewed masks and broader fixed-map support."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import shutil
import subprocess
import time
import numpy as np
from PIL import Image,ImageDraw
import _bootstrap
from skate4d.dataset import ROOT
from estimate_fullrate_poses import Localizer,write_json,fingerprint


def retry_mask(config,width,height,score_visible):
    x,y,_,_=config['crop_xywh']
    mask=Image.new('L',(width,height),255)
    rectangles=[[260,540,500,760],[230,650,570,900]]
    if score_visible:
        rectangles.append([64,180,656,350])
    draw=ImageDraw.Draw(mask)
    for a,b,c,d in rectangles:
        draw.rectangle([a-x,b-y,c-x-1,d-y-1],fill=0)
    return mask


def retry(work,resume=False):
    started=time.monotonic()
    previous_retry={}
    if (work/'retry-report.json').exists() and not resume:
        raise ValueError('Retry report exists; inspect before another attempt')
    if (work/'retry-report.json').exists():
        previous_retry=json.loads((work/'retry-report.json').read_text())
    config=json.loads((work/'run-config.json').read_text(encoding='utf-8'))
    report=json.loads((work/'report.json').read_text(encoding='utf-8'))
    baseline=json.loads((work/'poses.json').read_text(encoding='utf-8'))
    # Verify the observed score-onset condition rather than silently assuming it.
    score=json.loads((ROOT/'outputs/capture-inspection/score-sync-check.json').read_text())
    onsets=[c['first_score_frame_zero_based'] for c in score['cameras']]
    if any(i is None or i<97 for i in onsets):
        raise ValueError('The capture-specific pre-score mask rule is not supported by the event audit')
    for name in ['poses','report']:
        target=work/f'{name}.initial.json'
        if not target.exists():
            shutil.copy2(work/f'{name}.json',target)
    loc=Localizer(ROOT/config['reference'],Path(config['dataset']),feature_limit=8192)
    if fingerprint(loc.source)!=config['source_sha256']:
        raise ValueError('Source recording changed')
    failed={r['camera_id'] for r in baseline['frames'] if r['status']=='failed'}
    if not failed:
        print('No failed frames remain; reports preserved.')
        return
    recovered=[];remaining=[]
    for passage in sorted(failed):
        part=work/'passages'/f'{passage}.json'
        rows=json.loads(part.read_text(encoding='utf-8'))['frames']
        first=next(c['first_frame'] for c in loc.cuts['candidates'] if c['id']==passage)
        count=loc.cuts['frames_per_clip'];fps=float(Fraction(loc.cuts['fps']))
        x,y,w,h=loc.config['crop_xywh']
        raw=subprocess.run(['ffmpeg','-nostdin','-v','error','-ss',f'{first/fps:.9f}',
            '-i',str(loc.source),'-vf',f'crop={w}:{h}:{x}:{y}','-frames:v',str(count),
            '-fps_mode','passthrough','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],
            capture_output=True,check=True).stdout
        if len(raw)!=count*w*h*3:
            raise ValueError('Unexpected decoded clip length')
        images=np.frombuffer(raw,np.uint8).reshape(count,h,w,3)
        for row in rows:
            if row['status']!='failed':
                continue
            i=row['clip_frame_index']
            mask=retry_mask(loc.config,w,h,i>=97)
            loc.mask=np.asarray(mask)
            result=loc.solve(images[i],passage,i,native_gray=True,expanded_refs=True)
            if result['status']=='localized':
                row.pop('reason',None)
                row.update(result)
                row['method']='fixed_map_sift_pnp_ransac_retry'
                row['retry_settings']='8192 features; native grayscale; expanded anchor retrieval; reviewed board mask; score band only from index 97'
                recovered.append(row['image_path'])
            else:
                row['retry_quality']=result.get('quality')
                remaining.append(row['image_path'])
        # Very weak backgrounds can benefit from feature tracks in adjacent
        # already-localized images. Promote only geometrically validated 2D-3D
        # support; the target still needs a new PnP solve with the same thresholds.
        for row in rows:
            if row['status']!='failed':
                continue
            i=row['clip_frame_index']
            neighbors=[j for j in [i-1,i+1] if 0<=j<len(rows) and rows[j]['status']=='localized']
            for j in neighbors:
                loc.mask=np.asarray(retry_mask(loc.config,w,h,j>=97))
                neighbor=loc.solve(images[j],passage,j,native_gray=True,expanded_refs=True,include_support=True)
                if neighbor['status']=='localized':
                    support=neighbor.pop('_support')
                    loc.anchors[passage].append(dict(name=rows[j]['image_path'],index=j,
                        matrix=np.asarray(neighbor['world_to_camera']),**support))
            loc.mask=np.asarray(retry_mask(loc.config,w,h,i>=97))
            result=loc.solve(images[i],passage,i,native_gray=True,expanded_refs=True)
            if result['status']=='localized':
                row.pop('reason',None);row.pop('retry_quality',None);row.update(result)
                row['method']='fixed_map_sift_pnp_ransac_neighbor_support'
                row['retry_settings']='Promoted PnP-inlier feature tracks from adjacent localized images; same map and acceptance filters; no interpolation'
                recovered.append(row['image_path'])
        write_json(part,dict(camera_id=passage,frames=rows))
        print(f'Retry {passage}: {sum(r["status"]=="localized" for r in rows)}/{len(rows)}',flush=True)
    rows=[]
    for passage in loc.config['training_passages']:
        rows.extend(json.loads((work/'passages'/f'{passage}.json').read_text())['frames'])
    good=[r for r in rows if r['method']!='inherited_sparse_anchor' and r['status']=='localized']
    errors=[r['quality']['mean_error_px'] for r in good]
    report.update(localized_frames=sum(r['status']=='localized' for r in rows),
        new_localized_frames=len(good),failed_frames=sum(r['status']=='failed' for r in rows),
        per_passage={n:sum(r['status']=='localized' for r in rows if r['camera_id']==n) for n in loc.config['training_passages']},
        pnp_frame_mean_error_average_px=float(np.mean(errors)),pnp_frame_mean_error_p95_px=float(np.quantile(errors,.95)),
        retry_elapsed_seconds=report.get('retry_elapsed_seconds',0)+time.monotonic()-started,
        recovered_in_retry=report.get('recovered_in_retry',0)+len(recovered),
        failed_images=[r['image_path'] for r in rows if r['status']=='failed'])
    write_json(work/'poses.json',dict(camera=baseline['camera'],frames=rows))
    write_json(work/'report.json',report)
    for visible,label in [(False,'pre-score'),(True,'score-visible')]:
        retry_mask(loc.config,loc.width,loc.height,visible).save(work/f'retry-mask-{label}.png')
    retry_report=dict(recovered=previous_retry.get('recovered',[])+recovered,remaining=report['failed_images'],thresholds_unchanged=True,
        references_unchanged=True,feature_limit=8192,grayscale='native COLMAP bitmap',
        mask_rule='source rectangles [260,540,500,760], [230,650,570,900]; score band [64,180,656,350] only at index >=97',
        score_audit_sha256=fingerprint(ROOT/'outputs/capture-inspection/score-sync-check.json'),
        neighbor_support='For residual failures, matched 2D-3D inlier tracks from accepted adjacent images; no pose interpolation or new map points',
        elapsed_seconds=previous_retry.get('elapsed_seconds',0)+time.monotonic()-started)
    write_json(work/'retry-report.json',retry_report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('workspace',type=Path,nargs='?',default=ROOT/'outputs/replay-fullrate-poses')
    p.add_argument('--resume',action='store_true',help='Retry only still-failed rows after a previous retry report')
    args=p.parse_args()
    retry(args.workspace,args.resume)
