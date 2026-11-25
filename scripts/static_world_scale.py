"""Uniform scene similarity for the undeformed renderer; preserve pinhole projections."""
import math
from types import SimpleNamespace

CUDA_NEAR_DEPTH=.2


def board_depth_report(points,records,near=CUDA_NEAR_DEPTH):
    import numpy as np
    result={}
    for record in records:
        pose=np.array(record['world_to_camera'])
        z=(points@pose[:,:3].T+pose[:,3])[:,2]
        result[record['camera_id']]=dict(min_depth=float(z.min()),median_depth=float(np.median(z)),
            max_depth=float(z.max()),fraction_above_near=float(np.mean(z>near)))
    return result


def training_scale(points,records,target_depth=.3):
    train=[r for r in records if r['split']=='train']
    if not train:raise ValueError('No training views')
    depths=board_depth_report(points,train)
    minimum=min(d['min_depth'] for d in depths.values())
    if not math.isfinite(minimum) or minimum<=0:raise ValueError('Board is behind a training camera')
    factor=2.**max(0,math.ceil(math.log2(target_depth/minimum)))
    return factor,minimum


def require_board_visibility(points,records,near=CUDA_NEAR_DEPTH):
    report=board_depth_report(points,records,near)
    failing=[name for name,row in report.items() if row['fraction_above_near']<1.]
    if failing:raise ValueError('Board seeds hit the CUDA near plane in '+', '.join(failing)+'; prepare a safe dataset with scripts/prepare_safe_static_scale.py')
    return report


def scaled_camera(camera,factor):
    if not math.isfinite(factor) or factor<=0:raise ValueError('Scale must be finite and positive')
    view=camera.world_view_transform.clone()
    view[3,:3]*=factor
    return SimpleNamespace(FoVx=camera.FoVx,FoVy=camera.FoVy,image_height=camera.image_height,image_width=camera.image_width,
        world_view_transform=view,full_proj_transform=view@camera.projection_matrix,
        camera_center=camera.camera_center*factor,time=camera.time)


def scaled_gaussians(model,factor,select=None,white=False):
    import torch
    if not math.isfinite(factor) or factor<=0:raise ValueError('Scale must be finite and positive')
    xyz=model.get_xyz
    select=torch.ones(len(xyz),device=xyz.device,dtype=torch.bool) if select is None else select
    features=model.get_features[select].clone()
    if white:
        features.zero_();features[:,0,:]=.5/.28209479177387814
    return SimpleNamespace(get_xyz=xyz[select]*factor,_opacity=model._opacity[select],get_features=features,
        _scaling=model._scaling[select]+math.log(factor),_rotation=model._rotation[select],_deformation_table=model._deformation_table[select],
        active_sh_degree=0 if white else model.active_sh_degree,max_sh_degree=model.max_sh_degree,
        scaling_activation=model.scaling_activation,rotation_activation=model.rotation_activation,opacity_activation=model.opacity_activation)
