"""Single-instant, training-only silhouette consistency check; not measured surface geometry."""
import argparse
from collections import deque
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from prepare_dense_fixed_init import write_cloud


def largest_component(mask):
    remaining=mask.copy();best=[]
    for y,x in zip(*np.where(mask)):
        if not remaining[y,x]:continue
        component=[];queue=deque([(int(y),int(x))]);remaining[y,x]=False
        while queue:
            a,b=queue.popleft();component.append((a,b))
            for dy,dx in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                c,d=a+dy,b+dx
                if 0<=c<mask.shape[0] and 0<=d<mask.shape[1] and remaining[c,d]:
                    remaining[c,d]=False;queue.append((c,d))
        if len(component)>len(best):best=component
    result=np.zeros_like(mask)
    if best:
        coords=np.array(best);result[coords[:,0],coords[:,1]]=True
    return result


def project(points,pose,intrinsics):
    camera=points@pose[:,:3].T+pose[:,3]
    f,cx,cy=intrinsics
    pixels=camera[:,:2]/camera[:,2,None]
    return pixels*f+[cx,cy],camera[:,2]


def triangulate_centers(centers,poses,intrinsics):
    f,cx,cy=intrinsics
    k=np.array([[f,0,cx],[0,f,cy],[0,0,1]])
    rows=[]
    for pixel,pose in zip(centers,poses):
        p=k@pose
        rows.extend([pixel[0]*p[2]-p[0],pixel[1]*p[2]-p[1]])
    _,_,v=np.linalg.svd(rows)
    return v[-1,:3]/v[-1,3]


def run(source,geometry,output,sample=8,resolution=128,exclude=(),skip_carving=(),skip_small_masks=False):
    if output.exists():raise ValueError('Choose a fresh output')
    output.mkdir(parents=True)
    manifest=json.loads((source/'manifest.json').read_text())
    records=[r for r in manifest['frames'] if Path(r['image_path']).stem==f'{sample:03d}']
    training=[r for r in records if r['split']=='train' and r['camera_id'] not in exclude]
    carving=[r for r in training if r['camera_id'] not in skip_carving]
    test=[r for r in records if r['split']=='test']
    if len(carving)<3 or len(test)!=1:raise ValueError('Need at least three carving views and one reserved view')
    masks={};images={};descriptions=[]
    for record in training+test:
        name=record['camera_id']
        targets=np.stack([np.array(Image.open(source/f'images/{name}/{i:03d}.png').convert('RGB')) for i in range(13)])
        if name=='view19':background=np.array(Image.open(source/'background/view19.png').convert('RGB'))
        else:
            # The whole-clip SfM median may retain the long stationary start pose.
            # Use the moving action window instead, to avoid selecting its ghost.
            background=np.median(targets,axis=0).astype(np.uint8)
        change=np.ptp(targets.astype(np.int16),axis=0).max(2)>45
        target=targets[sample]
        candidate=(np.abs(target.astype(np.int16)-background.astype(np.int16)).max(2)>40)&change
        candidate[:400]=False;candidate[1200:]=False
        mask=largest_component(candidate)
        if mask.sum()<=20 and not skip_small_masks:raise ValueError(f'Insufficient foreground in {name}')
        masks[name]=mask;images[name]=target
        ys,xs=np.where(mask)
        descriptions.append(dict(camera=name,split=record['split'],pixels=int(mask.sum()),bbox=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())] if len(xs) else None,
            center=[float(xs.mean()),float(ys.mean())] if len(xs) else None,raw_candidate_pixels=int(candidate.sum()),usable_region=bool(mask.sum()>20)))
        (output/'masks').mkdir(exist_ok=True)
        Image.fromarray(mask.astype(np.uint8)*255).save(output/'masks'/f'{name}.png')
    sheet=Image.new('RGB',(6*240,3*365),'white');draw=ImageDraw.Draw(sheet)
    for i,description in enumerate(descriptions):
        name=description['camera'];target=images[name].copy();mask=masks[name]
        target[mask]=(target[mask]*.4+[0,150,0]).clip(0,255).astype(np.uint8)
        tile=Image.fromarray(target).crop((0,400,563,1200)).resize((240,341))
        x,y=(i%6)*240,(i//6)*365
        sheet.paste(tile,(x,y+24));draw.text((x+4,y+6),f'{name} {description["pixels"]}px {description["split"]}',fill='black')
    sheet.save(output/'mask-review.jpg',quality=94)
    too_small={d['camera'] for d in descriptions if not d['usable_region']}
    carving=[r for r in carving if r['camera_id'] not in too_small]
    if len(carving)<3:raise ValueError('Fewer than three usable carving masks')
    carving_ids={r['camera_id'] for r in carving}
    poses=[np.array(r['world_to_camera']) for r in carving]
    centers=np.array([d['center'] for d in descriptions if d['camera'] in carving_ids])
    center=triangulate_centers(centers,poses,manifest['intrinsics'])
    reprojections=[project(center[None],p,manifest['intrinsics']) for p in poses]
    errors=np.array([np.linalg.norm(uv[0]-pixel) for (uv,_),pixel in zip(reprojections,centers)])
    depths=np.array([z[0] for _,z in reprojections])
    spans=np.array([max(d['bbox'][2]-d['bbox'][0],d['bbox'][3]-d['bbox'][1]) for d in descriptions if d['camera'] in carving_ids])
    half=float(np.percentile(spans*np.abs(depths)/manifest['intrinsics'][0],75))
    if not np.isfinite(half) or half<=0 or not np.all(depths>0):raise ValueError('Invalid candidate center')
    axis=np.linspace(-half,half,resolution)
    points=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),-1).reshape(-1,3).astype(np.float32)+center
    votes=np.zeros(len(points),np.uint8)
    for record,pose in zip(carving,poses):
        # Two-pixel dilation at training resolution tolerates small mask/calibration errors.
        mask=np.array(Image.fromarray(masks[record['camera_id']].astype(np.uint8)*255).filter(ImageFilter.MaxFilter(5)))>0
        for start in range(0,len(points),100000):
            uv,z=project(points[start:start+100000],pose,manifest['intrinsics'])
            pixels=np.rint(uv).astype(int);x,y=pixels.T
            inside=(z>0)&(x>=0)&(x<mask.shape[1])&(y>=0)&(y<mask.shape[0])
            hit=np.zeros(len(uv),bool);hit[inside]=mask[y[inside],x[inside]]
            votes[start:start+len(uv)]+=hit
        print('Carved',record['camera_id'],flush=True)
    strict=points[votes==len(carving)]
    relaxed=points[votes>=len(carving)-2]
    for name,cloud in [('strict-hull',strict),('relaxed-hull',relaxed)]:
        write_cloud(output/(name+'.ply'),cloud.astype(np.float32),np.tile(np.array([[60,180,230]],np.uint8),(len(cloud),1)))
    report=dict(sample_index=sample,seconds_before_score=float(training[0]['seconds_relative_to_score']),training_views=len(training),reserved_view=manifest['heldout_camera'],
        carving_views=[r['camera_id'] for r in carving],excluded_views=list(exclude),skipped_carving_views=list(skip_carving),
        small_mask_views=sorted(too_small),small_mask_policy='Keep RGB training images; omit <=20-pixel masks from carving/loss and mark region metrics unavailable' if skip_small_masks else 'Reject <=20-pixel masks',
        masks=descriptions,center=center.tolist(),center_reprojection_error_pixels=errors.tolist(),median_center_error_pixels=float(np.median(errors)),
        candidate_cube_half_extent=half,resolution=resolution,grid_points=len(points),voxel_spacing=2*half/(resolution-1),
        tolerance_pixels=2,strict_intersection_voxels=len(strict),relaxed_intersection_voxels=len(relaxed),relaxed_min_views=len(carving)-2,max_consistent_views=int(votes.max()),
        vote_histogram=np.bincount(votes,minlength=len(carving)+1).tolist(),heldout_used_for_carving=False,
        gate_passed=bool(len(strict)>=30),
        mask_background='13-sample action-window temporal median, except the true empty view18 reference for view19',
        caveat='Candidate masks, not semantic ground truth. Centers are silhouette centroids, not corresponding physical keypoints. Visual hull is a silhouette-derived volume, not measured surface points. Shared cameras and timing remain estimated.')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['masks','center_reprojection_error_pixels']},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-clean-pilot'))
    p.add_argument('--geometry',type=Path,default=Path('outputs/clean-replay-pipeline/geometry'))
    p.add_argument('--output',type=Path,default=Path('outputs/static-board-geometry'))
    p.add_argument('--sample',type=int,default=8,choices=range(13))
    p.add_argument('--resolution',type=int,default=128)
    p.add_argument('--exclude-views',nargs='*',default=[])
    p.add_argument('--skip-carving-views',nargs='*',default=[])
    p.add_argument('--skip-small-masks',action='store_true')
    a=p.parse_args();run(a.source,a.geometry,a.output,a.sample,a.resolution,a.exclude_views,a.skip_carving_views,a.skip_small_masks)
