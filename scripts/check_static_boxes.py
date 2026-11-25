"""Check global 3D feasibility of generous board boxes, independent of voxel search bounds."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog


def constraints(records,boxes,intrinsics,padding=0):
    rows=[];bounds=[]
    for record in records:
        f,cx,cy=record.get('intrinsics',intrinsics)
        k=np.array([[f,0,cx],[0,f,cy],[0,0,1]])
        pose=np.array(record['world_to_camera']);p=k@pose
        left,top,right,bottom=boxes[record['camera_id']]
        for q in [p[0]-(right+padding)*p[2],(left-padding)*p[2]-p[0],
                  p[1]-(bottom+padding)*p[2],(top-padding)*p[2]-p[1]]:
            rows.append(q[:3]);bounds.append(-q[3])
        rows.append(-pose[2,:3]);bounds.append(pose[2,3]-.001)
    return np.array(rows),np.array(bounds)


def feasible(records,boxes,intrinsics,padding=0):
    a,b=constraints(records,boxes,intrinsics,padding)
    solution=linprog(np.zeros(3),A_ub=a,b_ub=b,bounds=[(None,None)]*3,method='highs')
    if solution.status not in [0,2]:raise ValueError('Unexpected LP status: '+solution.message)
    return dict(feasible=bool(solution.success),solver_status=int(solution.status),
        point=solution.x.tolist() if solution.success else None)


def run(source,geometry,output):
    manifest=json.loads((source/'manifest.json').read_text())
    initial=json.loads((geometry/'report.json').read_text())
    sample=initial['sample_index']
    records=[r for r in manifest['frames'] if r['split']=='train' and Path(r['image_path']).stem==f'{sample:03d}']
    boxes={r['camera']:[r['bbox'][0]-8,r['bbox'][1]-8,r['bbox'][2]+8,r['bbox'][3]+8] for r in initial['masks'] if r['split']=='train'}
    # Visually inspected conservative boxes for incomplete, low-contrast masks.
    overrides={'view07':[155,635,285,695],'view11':[255,620,305,680]}
    boxes.update(overrides)
    result=dict(sample_index=sample,seconds_before_score=initial['seconds_before_score'],boxes=boxes,
        box_method='Largest-component bounds expanded by eight pixels, except manually reviewed generous view07/view11 boxes',
        manual_overrides=overrides,all_17=feasible(records,boxes,manifest['intrinsics']),
        all_17_with_2px_extra=feasible(records,boxes,manifest['intrinsics'],2),
        exploratory_14=feasible([r for r in records if r['camera_id'] not in ['view07','view08','view09']],boxes,manifest['intrinsics']),
        exploratory_excluded_views=['view07','view08','view09'],heldout_used=False,
        criterion='One 3D point must project inside every bounding box with positive depth. Necessary for a common board point, not sufficient for a correct surface.',
        limitations='Numerical LP on approximate observations and estimated cameras, not proof of physical impossibility. Coarse silhouettes, residual timing, calibration and replay consistency remain possible explanations.')
    low,high=0.,160.
    if feasible(records,boxes,manifest['intrinsics'],high)['feasible']:
        for _ in range(16):
            mid=(low+high)/2
            if feasible(records,boxes,manifest['intrinsics'],mid)['feasible']:high=mid
            else:low=mid
        result['minimum_uniform_extra_padding_pixels_approx']=high
    else:result['minimum_uniform_extra_padding_pixels_approx']=None
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-clean-pilot'))
    p.add_argument('--geometry',type=Path,default=Path('outputs/static-board-geometry-v2'))
    p.add_argument('--output',type=Path,default=Path('outputs/static-board-geometry-v2/box-feasibility.json'))
    a=p.parse_args();run(a.source,a.geometry,a.output)
