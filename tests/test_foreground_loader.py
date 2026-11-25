"""Exercise the actual upstream Camera mask path and reject heldout masks."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


@unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('diff_gaussian_rasterization'),
                     'Configured GPU environment supplies upstream dependencies')
class ForegroundLoaderTests(unittest.TestCase):
    def test_mask_reaches_actual_camera_and_heldout_mask_is_rejected(self):
        sys.path.insert(0,str(ROOT/'third_party/4DGaussians'))
        import numpy as np
        from PIL import Image
        from fixed_dataset_adapter import install
        from scene.dataset_readers import sceneLoadTypeCallbacks
        from scene.dataset import FourDGSdataset
        from prepare_dense_fixed_init import write_cloud
        install()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            Image.new('RGB',(4,4),(120,80,40)).save(root/'image.png')
            mask=np.zeros((4,4),np.uint8);mask[1,2]=255
            Image.fromarray(mask).save(root/'mask.png')
            write_cloud(root/'points3D_multipleview.ply',np.array([[0,0,2],[.1,.1,2]],np.float32),np.full((2,3),100,np.uint8))
            pose=[[1,0,0,0],[0,1,0,0],[0,0,1,0]]
            frames=[dict(camera_id=name,split=split,image_path='image.png',time=t,world_to_camera=pose)
                    for name,split,t in [('train','train',0),('reserved','test',1)]]
            frames[0]['foreground_mask_path']='mask.png'
            manifest=dict(image_resolution=[4,4],intrinsics=[3,2,2],frames=frames,
                          training_cameras=['train'],heldout_camera='reserved')
            (root/'manifest.json').write_text(json.dumps(manifest))
            scene=sceneLoadTypeCallbacks['MultipleView'](root)
            camera=FourDGSdataset(scene.train_cameras,None,'MultipleView')[0]
            self.assertEqual(int(camera.mask.sum()),1)
            self.assertTrue(camera.mask[1,2])
            self.assertIsNone(FourDGSdataset(scene.test_cameras,None,'MultipleView')[0].mask)
            frames[1]['foreground_mask_path']='mask.png'
            (root/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Heldout'):
                sceneLoadTypeCallbacks['MultipleView'](root)


if __name__=='__main__':unittest.main()
