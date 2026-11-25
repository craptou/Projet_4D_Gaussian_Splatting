"""Exploratory training-only timing search around one selected static instant."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image,ImageDraw
from static_board_geometry import largest_component,project,triangulate_centers


def run(source,clips,geometry,output):
    if output.exists():raise ValueError('Choose fresh output')
    output.mkdir(parents=True)
    manifest=json.loads((source/'manifest.json').read_text())
    geo=json.loads((geometry/'report.json').read_text())
    descriptions={r['camera']:r for r in geo['masks']}
    records={r['camera_id']:r for r in manifest['frames'] if r['split']=='train' and Path(r['image_path']).stem=='008'}
    anchors=[r for name,r in records.items() if name not in ['view07','view08','view09','view11']]
    point=triangulate_centers([descriptions[r['camera_id']]['center'] for r in anchors],
        [np.array(r['world_to_camera']) for r in anchors],manifest['intrinsics'])
    cuts={r['id']:r for r in json.loads((clips/'cuts.json').read_text())['candidates']}
    rows=[];sheet=Image.new('RGB',(900,3*456),'white');draw=ImageDraw.Draw(sheet)
    for row,name in enumerate(['view07','view08','view09']):
        record=records[name];nominal=record['clip_frame']
        low=max(0,nominal-18);high=min(cuts[name]['frames']-1,nominal+30)
        raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-hwaccel','cuda','-i',str(clips/cuts[name]['file_path']),
            '-vf',f'select=between(n\\,{low}\\,{high}),scale=563:1218','-frames:v',str(high-low+1),
            '-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','pipe:1'])
        frames=np.frombuffer(raw,np.uint8).reshape(-1,1218,563,3)
        background=np.median(frames,axis=0).astype(np.int16)
        variation=np.ptp(frames.astype(np.int16),axis=0).max(2)>30
        expected,_=project(point[None],np.array(record['world_to_camera']),manifest['intrinsics'])
        candidates=[];masks=[]
        for i,image in enumerate(frames):
            mask=(np.abs(image.astype(np.int16)-background).max(2)>15)&variation
            mask[:400]=False;mask[1200:]=False
            mask=largest_component(mask);ys,xs=np.where(mask)
            if len(xs)<100:continue
            center=np.array([xs.mean(),ys.mean()]);distance=float(np.linalg.norm(center-expected[0]))
            candidates.append(dict(clip_frame=low+i,offset_frames=low+i-nominal,offset_seconds=(low+i-nominal)/60,
                center=center.tolist(),distance_to_projected_anchor_pixels=distance,mask_pixels=len(xs)))
            masks.append((i,mask))
        index=min(range(len(candidates)),key=lambda j:candidates[j]['distance_to_projected_anchor_pixels'])
        best=candidates[index];i,mask=masks[index]
        Image.fromarray(frames[i]).save(output/f'{name}.png')
        Image.fromarray(mask.astype(np.uint8)*255).save(output/f'{name}-mask.png')
        with Image.open(source/record['image_path']) as im:before=np.array(im.convert('RGB'))
        overlay=frames[i].copy();overlay[mask]=(overlay[mask]*.4+[0,150,0]).clip(0,255).astype(np.uint8)
        for column,(label,array) in enumerate([('Nominal sample8',before),('Best candidate',frames[i]),('Candidate mask',overlay)]):
            tile=Image.fromarray(array).crop((0,400,563,1200)).resize((300,426))
            sheet.paste(tile,(column*300,row*456+30));draw.text((column*300+4,row*456+8),f'{name}: {label} / offset {best["offset_frames"]}',fill='black')
        rows.append(dict(camera=name,nominal_clip_frame=nominal,projected_anchor=expected[0].tolist(),selected=best,candidates=candidates))
        print(name,json.dumps(best),flush=True)
    sheet.save(output/'timing-review.jpg',quality=94)
    report=dict(anchor_point=point.tolist(),anchor_views=[r['camera_id'] for r in anchors],search=rows,
        heldout_used=False,caution='Single-instant centroid alignment hypothesis. Masks and silhouette centroids are approximate. Not proof of full-sequence synchronization; requires visual review and geometric recheck.')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-clean-pilot'))
    p.add_argument('--clips',type=Path,default=Path('data/raw/true-skate-clean-2026-11-24'))
    p.add_argument('--geometry',type=Path,default=Path('outputs/static-board-geometry-v2'))
    p.add_argument('--output',type=Path,default=Path('outputs/static-board-timing'))
    a=p.parse_args();run(a.source,a.clips,a.geometry,a.output)
