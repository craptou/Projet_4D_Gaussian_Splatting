"""Read-only camera lesson: run the toy example, then inspect one real project camera."""
import argparse
import json
from pathlib import Path
import numpy as np
from static_board_geometry import project
from prepare_dense_fixed_init import read_cloud


def toy():
    # A camera looking along +Z, positioned at X=1 in world coordinates.
    rotation=np.eye(3)
    center=np.array([1.,0.,0.])
    translation=-rotation@center
    pose=np.c_[rotation,translation]
    intrinsics=[400.,300.,200.]
    points=np.array([[2.,0.,4.],[2.,0.,8.]])
    pixels,depth=project(points,pose,intrinsics)
    print('World points:\n',points)
    print('Camera center C:',center)
    print('World-to-camera translation t:',translation)
    print('Camera coordinates:\n',points@rotation.T+translation)
    print('Pixels, with f=400 and principal point (300,200):\n',pixels)
    print('Depths:',depth)
    print('Doubling depth moves this point closer to the image center.')
    print('Recovering the camera center from the pose:',-rotation.T@translation)
    assert np.array_equal(pixels,np.array([[400.,200.],[350.,200.]]))


def real(source,view):
    manifest=json.loads((source/'manifest.json').read_text())
    record=next(r for r in manifest['frames'] if r['camera_id']==view)
    pose=np.array(record['world_to_camera']);rotation=pose[:,:3];translation=pose[:,3]
    center=-rotation.T@translation
    print('Source:',source,'/ camera:',view,'/ sample:',record['sample_index'])
    print('Intrinsics [f,cx,cy]:',manifest['intrinsics'])
    print('R:\n',rotation,'\nt:',translation,'\nC=-R.T@t:',center)
    print('Camera center transformed into its own frame:',rotation@center+translation)
    print('Rotation check R.T@R:\n',rotation.T@rotation)
    print('Rotation determinant:',np.linalg.det(rotation))
    xyz,_=read_cloud(source/'points3D_multipleview.ply')
    start=json.loads((source/'preparation.json').read_text())['background_points']
    point=xyz[start:].mean(0,keepdims=True)
    pixels,depth=project(point,pose,manifest['intrinsics'])
    print('Mean of initial silhouette-volume seeds:',point[0])
    print('Its projected pixel:',pixels[0],'/ camera depth:',depth[0])
    print('This is a synthetic volume center, not a tracked material point.')
    print('World coordinates have arbitrary scene units, not known meters.')
    assert np.allclose(rotation@center+translation,0,atol=1e-6)
    assert np.allclose(rotation.T@rotation,np.eye(3),atol=1e-6)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--real',action='store_true')
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-dense-comparison'))
    p.add_argument('--view',default='view20')
    a=p.parse_args()
    if a.real:real(a.source,a.view)
    else:toy()
