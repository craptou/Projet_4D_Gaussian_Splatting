"""Check segmentation encoding, held-out exclusion and dense-time evaluation contracts."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from dynamic_replay_engine import export
from prepare_dense_replay import action_masks
from review_dynamic_comparison import psnr,overlap
from evaluate_joint_replay import evaluation_groups


class DynamicComparisonTests(unittest.TestCase):
    def test_export_only_training_and_zero_one_masks(self):
        with TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';source.mkdir();work=Path(tmp)/'work'
            Image.fromarray(np.zeros((6,9,3),np.uint8)).save(source/'train.png')
            mask=np.array([[0,255,255],[255,255,255]],np.uint8)
            # More than20 pixels is required by the real exporter.
            mask=np.tile(mask,(3,3));Image.fromarray(mask).save(source/'mask.png')
            pose=np.c_[np.eye(3),np.zeros(3)].tolist()
            frames=[dict(camera_id='view01',sample_index=3,split='train',image_path='train.png',foreground_mask_path='mask.png',world_to_camera=pose),
                dict(camera_id='view20',sample_index=3,split='test',image_path='DOES-NOT-EXIST.png',world_to_camera=pose)]
            manifest=dict(temporal_scene=True,training_cameras=['view01'],heldout_camera='view20',sample_indices=[3],frames=frames,image_resolution=[9,6],intrinsics=[1.,4.5,3.])
            (source/'manifest.json').write_text(json.dumps(manifest));(source/'preparation.json').write_text(json.dumps(dict(background_points=2)))
            xyz=np.arange(12,dtype=np.float32).reshape(4,3);rgb=np.full((4,3),128,np.uint8)
            with patch('dynamic_replay_engine.read_cloud',return_value=(xyz,rgb)):
                _,metadata=export(source,work)
            self.assertEqual(metadata['fn'],[['view01/003.png']])
            with Image.open(work/'data/replay/seg/view01/003.png') as im:actual=np.array(im)
            np.testing.assert_array_equal(actual,mask>0)
            self.assertEqual(set(np.unique(actual)),{0,1})
            cloud=np.load(work/'data/replay/init_pt_cld.npz')['data']
            np.testing.assert_array_equal(cloud[:,6],[0,0,1,1])
            np.testing.assert_array_equal(cloud[:,:3],xyz)
            np.testing.assert_allclose(cloud[:,3:6],128/255)

    def test_dense_times_do_not_create_empty_unseen_group(self):
        self.assertEqual(evaluation_groups([3,4,5],{3,4,5}),{'observed':[0,1,2]})
        self.assertEqual(evaluation_groups([3,4,5],{3,5}),{'observed':[0,2],'unseen_time':[1]})

    def test_masks_reject_static_and_outside_action_area(self):
        images=[np.zeros((402,2,3),np.uint8) for _ in range(13)]
        images[3][400,0]=200;images[3][399,1]=200
        masks=action_masks(images)
        self.assertTrue(masks[3][400,0]);self.assertFalse(masks[3][399,1])
        self.assertFalse(masks[4].any())

    def test_regional_error_can_worsen_when_full_image_improves(self):
        target=np.zeros((10,10,3),np.uint8);mask=np.zeros((10,10),bool);mask[0,0]=True
        a=np.full_like(target,50);a[0,0]=0
        b=np.zeros_like(target);b[0,0]=255
        self.assertGreater(psnr(b,target),psnr(a,target))
        self.assertLess(psnr(b,target,mask),psnr(a,target,mask))
        self.assertIsNone(overlap(np.zeros((2,2),bool),np.zeros((2,2),bool)))


if __name__=='__main__':unittest.main()
