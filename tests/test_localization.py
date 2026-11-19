"""Geometric support and correspondence safety regressions (optional SfM extras)."""
import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
HAS_NUMPY=importlib.util.find_spec('numpy') is not None
HAS_PYCOLMAP=importlib.util.find_spec('pycolmap') is not None
if HAS_NUMPY:
    import numpy as np
    from skate4d.localization import accepted,pose_quality,unique_correspondences


@unittest.skipUnless(HAS_NUMPY,'Install project SfM extras for localization tests')
class LocalizationTests(unittest.TestCase):
    def test_conflicting_points_and_duplicate_tracks_excluded(self):
        votes={0:{10},1:{11,12},2:{10},3:{13}}
        self.assertEqual(unique_correspondences(votes),[(0,10),(3,13)])

    def test_known_camera_reprojection_and_depth(self):
        rng=np.random.default_rng(0)
        points=rng.uniform(-1,1,(80,3));points[:,2]+=5
        matrix=np.c_[np.eye(3),[.2,-.1,1.0]]
        xyz=points@matrix[:,:3].T+matrix[:,3]
        pixels=xyz[:,:2]/xyz[:,2,None]*500+[300,400]
        quality=pose_quality(pixels,points,matrix,np.ones(80,bool),[500,300,400])
        self.assertLess(quality['median_error_px'],1e-10)
        self.assertTrue(accepted(quality))
        shifted=pixels+20
        self.assertFalse(accepted(pose_quality(shifted,points,matrix,np.ones(80,bool),[500,300,400])))

    def test_behind_camera_rejected_even_with_zero_residual(self):
        points=np.tile([1,1,-5.0],(40,1))
        pixels=points[:,:2]/points[:,2,None]*500+[300,400]
        quality=pose_quality(pixels,points,np.c_[np.eye(3),[0,0,0]],np.ones(40,bool),[500,300,400])
        self.assertEqual(quality['positive_depth_ratio'],0)
        self.assertFalse(accepted(quality))

    def test_too_few_inliers_rejected(self):
        quality=dict(inliers=29,inlier_ratio=1,median_error_px=0,mean_error_px=0,positive_depth_ratio=1)
        self.assertFalse(accepted(quality))

    def test_no_inliers_has_explicit_error(self):
        with self.assertRaisesRegex(ValueError,'Invalid'):
            pose_quality([[0,0]],[[0,0,1]],np.c_[np.eye(3),[0,0,0]],[False],[1,0,0])

    @unittest.skipUnless(HAS_PYCOLMAP,'Install PyCOLMAP for synthetic pose-recovery test')
    def test_pnp_recovers_known_pose_despite_outliers(self):
        import pycolmap
        rng=np.random.default_rng(5)
        points=rng.uniform([-2,-1,4],[2,1,8],(120,3))
        angle=.2
        rotation=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
        translation=np.array([.3,-.15,.5])
        xyz=points@rotation.T+translation
        pixels=xyz[:,:2]/xyz[:,2,None]*443.8+[296,540]
        pixels+=rng.normal(0,.2,pixels.shape)
        pixels[:15]=rng.uniform([0,0],[592,820],(15,2))
        camera=pycolmap.Camera(model='SIMPLE_PINHOLE',width=592,height=820,params=[443.8,296,540])
        options=pycolmap.AbsolutePoseEstimationOptions()
        options.ransac.max_error=4;options.ransac.random_seed=0
        result=pycolmap.estimate_and_refine_absolute_pose(pixels,points,camera,options)
        self.assertIsNotNone(result)
        matrix=result['cam_from_world'].matrix()
        self.assertLess(np.linalg.norm(matrix[:,3]-translation),.05)
        self.assertLess(np.linalg.norm(matrix[:,:3]-rotation),.01)
        self.assertGreaterEqual(result['num_inliers'],100)


if __name__=='__main__':
    unittest.main()
