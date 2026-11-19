import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from prepare_pose_probe import build


class PosePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.video=self.base/'source.mp4'
        self.cuts=self.base/'cuts.json'
        self.cuts.write_text(json.dumps(dict(fps='6',resolution=[64,48],frames_per_clip=6,
            candidates=[dict(id='cam01',first_frame=0),dict(id='cam02',first_frame=3)])))
        self.config=dict(source=str(self.video),cuts=str(self.cuts),reserved_holdout='cam07',
            training_passages=['cam01','cam02'],sample_indices_zero_based=[0,2,5],
            crop_xywh=[4,4,56,40],mask_rectangles_original_xyxy=[[12,12,20,20]])
        self.path=self.base/'config.json'

    def save(self):
        self.path.write_text(json.dumps(self.config))

    def test_holdout_rejected_before_output(self):
        self.config['training_passages'].append('cam07')
        self.save()
        with self.assertRaisesRegex(ValueError,'Held-out'):
            build(self.path,self.base/'out')
        self.assertFalse((self.base/'out').exists())

    def test_bad_crop_rejected(self):
        self.config['crop_xywh']=[4,4,64,48]
        self.save()
        with self.assertRaisesRegex(ValueError,'Crop outside'):
            build(self.path,self.base/'out')

    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
    def test_real_extraction_and_mask_coordinates(self):
        subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i',
            'testsrc2=size=64x48:rate=6:duration=2','-c:v','libx264',str(self.video)],check=True)
        self.save()
        out=self.base/'out'
        build(self.path,out)
        manifest=json.loads((out/'manifest.json').read_text())
        self.assertEqual(len(manifest['frames']),6)
        self.assertEqual(manifest['frames'][-1]['source_frame_index'],8)
        self.assertEqual(manifest['frames'][-1]['time_seconds'],5/6)
        with Image.open(out/'images/cam02/frame_00006.png') as image:
            self.assertEqual(image.size,(56,40))
        with Image.open(out/'background-mask.png') as mask:
            self.assertEqual(mask.getpixel((8,8)),0)
            self.assertEqual(mask.getpixel((0,0)),255)
        with self.assertRaisesRegex(ValueError,'exists'):
            build(self.path,out)


if __name__=='__main__':
    unittest.main()
