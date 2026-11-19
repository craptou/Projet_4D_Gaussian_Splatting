"""Pure correspondence and pose-quality helpers for fixed-map localization."""
import numpy as np


def unique_correspondences(votes):
    """Keep only unambiguous query-to-point votes and unique 3D points."""
    pairs=[]
    used=set()
    for query,point_ids in sorted(votes.items()):
        if len(point_ids)!=1:
            continue
        point=next(iter(point_ids))
        if point in used:
            continue
        used.add(point)
        pairs.append((query,point))
    return pairs


def pose_quality(points2d,points3d,matrix,inlier_mask,intrinsics):
    """Measure positive-depth reprojection support, without modifying the pose."""
    p2=np.asarray(points2d,dtype=float)
    p3=np.asarray(points3d,dtype=float)
    pose=np.asarray(matrix,dtype=float)
    good=np.asarray(inlier_mask,dtype=bool)
    if len(p2)!=len(p3) or len(good)!=len(p2) or not good.any():
        raise ValueError('Invalid 2D/3D/inlier arrays')
    camera_points=p3@pose[:,:3].T+pose[:,3]
    f,cx,cy=intrinsics
    with np.errstate(divide='ignore',invalid='ignore'):
        pixels=camera_points[:,:2]/camera_points[:,2,None]*f+np.array([cx,cy])
    errors=np.linalg.norm(pixels-p2,axis=1)[good]
    return dict(correspondences=len(p2),inliers=int(good.sum()),inlier_ratio=float(good.mean()),
        median_error_px=float(np.median(errors)),mean_error_px=float(np.mean(errors)),
        p95_error_px=float(np.quantile(errors,.95)),
        positive_depth_ratio=float(np.mean(camera_points[good,2]>0)))


def accepted(quality):
    return (quality['inliers']>=30 and quality['inlier_ratio']>=.25
            and quality['median_error_px']<=2 and quality['mean_error_px']<=3
            and quality['positive_depth_ratio']>=.95)
