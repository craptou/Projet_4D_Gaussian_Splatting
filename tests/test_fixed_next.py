"""Scientific invariants for initialization resampling and fair comparisons."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
HAS_NUMPY=importlib.util.find_spec("numpy") is not None
if HAS_NUMPY:
    import numpy as np
    from PIL import Image
    from prepare_dense_fixed_init import resample
    from compare_fixed_runs import compare


@unittest.skipUnless(HAS_NUMPY,"Install project SfM extras")
class FixedNextTests(unittest.TestCase):
    def test_planar_geometry_and_linear_color_field_preserved(self):
        xyz=np.array([[x,y,2] for x in range(3) for y in range(3)],dtype=np.float32)
        rgb=np.c_[xyz[:,0]*100,xyz[:,1]*100,np.full(9,50)].astype(np.uint8)
        points,colors=resample(xyz,rgb,factor=8)
        np.testing.assert_array_equal(points[:9],xyz)
        self.assertEqual(len(points),72)
        np.testing.assert_array_equal(points[:,2],np.full(72,2))
        self.assertTrue(np.all((points[:,:2]>=0)&(points[:,:2]<=2)))
        self.assertLessEqual(np.max(np.abs(colors[:,:2].astype(float)-points[:,:2]*100)),.501)
        repeated,_=resample(xyz,rgb,factor=8)
        np.testing.assert_array_equal(points,repeated)

    def test_changed_evaluation_target_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,value in [("old",0),("new",1)]:
                run=root/name
                folder=run/"renders-2000/test-cam13/gt"
                folder.mkdir(parents=True)
                Image.new("RGB",(2,2),(value,0,0)).save(folder/"000.png")
                (run/"evaluation-2000.json").write_text(json.dumps({"metrics":{}}))
            with self.assertRaisesRegex(ValueError,"targets differ"):
                compare(root/"old",root/"new",root/"comparison")
