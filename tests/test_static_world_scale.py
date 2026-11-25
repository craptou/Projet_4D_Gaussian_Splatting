"""Prevent invisible board seeds while preserving calibrated screen projections."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


class NearClipGuardTests(unittest.TestCase):
    def test_training_only_factor_and_clipped_validation_are_distinct(self):
        import numpy as np
        from static_world_scale import training_scale,require_board_visibility
        points=np.array([[0.,0.,.1]])
        records=[dict(camera_id='train',split='train',world_to_camera=np.c_[np.eye(3),[0,0,0]].tolist()),
                 dict(camera_id='validation',split='test',world_to_camera=np.c_[np.eye(3),[0,0,-.099]].tolist())]
        factor,minimum=training_scale(points,records)
        self.assertEqual(factor,4.)
        with self.assertRaisesRegex(ValueError,'validation'):
            scaled=[]
            for row in records:
                pose=np.array(row['world_to_camera']);pose[:,3]*=factor
                scaled.append(dict(row,world_to_camera=pose.tolist()))
            require_board_visibility(points*factor,scaled)
        self.assertEqual(require_board_visibility(points*factor,scaled[:1])['train']['fraction_above_near'],1.)

    def test_scale_and_translation_preserve_pinhole_pixels(self):
        import numpy as np
        from static_board_geometry import project
        points=np.array([[.01,.02,.1],[.03,.01,.15]])
        pose=np.c_[np.eye(3),[.02,-.01,.03]]
        changed=pose.copy();changed[:,3]*=4
        np.testing.assert_allclose(project(points,pose,[422,281.5,609])[0],
                                   project(points*4,changed,[422,281.5,609])[0],atol=1e-10)

    def test_invalid_scale_rejected_before_camera_access(self):
        from static_world_scale import scaled_camera
        for value in [0,-1,float('nan')]:
            with self.assertRaises(ValueError):scaled_camera(None,value)


@unittest.skipUnless(importlib.util.find_spec('torch'),'WSL supplies torch')
class RuntimeSimilarityTests(unittest.TestCase):
    def test_runtime_camera_and_covariance_scale_without_mutation(self):
        import torch
        from static_world_scale import scaled_camera,scaled_gaussians
        view=torch.eye(4);view[3,2]=.07
        projection=torch.zeros(4,4);projection[0,0]=2;projection[1,1]=2
        projection[2,2]=1;projection[2,3]=1;projection[3,2]=-.01
        camera=SimpleNamespace(world_view_transform=view,projection_matrix=projection,camera_center=torch.tensor([0.,0.,-.07]),
            time=0.,FoVx=1.,FoVy=1.,image_height=8,image_width=8)
        xyz=torch.tensor([[.03,.01,.1]])
        original_view=view.clone();original_xyz=xyz.clone()
        model=SimpleNamespace(get_xyz=xyz,_opacity=torch.zeros(1,1),get_features=torch.zeros(1,1,3),
            _scaling=torch.tensor([[-4.,-5.,-6.]]),_rotation=torch.tensor([[1.,0.,0.,0.]]),_deformation_table=torch.ones(1,dtype=torch.bool),
            active_sh_degree=0,max_sh_degree=0,scaling_activation=torch.exp,rotation_activation=lambda x:x,opacity_activation=torch.sigmoid)
        new_camera=scaled_camera(camera,4.);new_model=scaled_gaussians(model,4.)
        a=torch.cat([xyz,torch.ones(1,1)],1)@(view@projection)
        b=torch.cat([new_model.get_xyz,torch.ones(1,1)],1)@new_camera.full_proj_transform
        torch.testing.assert_close(a[:,:2]/a[:,3:],b[:,:2]/b[:,3:])
        torch.testing.assert_close(torch.exp(new_model._scaling),torch.exp(model._scaling)*4)
        torch.testing.assert_close(camera.world_view_transform,original_view)
        torch.testing.assert_close(model.get_xyz,original_xyz)


if __name__=='__main__':unittest.main()
