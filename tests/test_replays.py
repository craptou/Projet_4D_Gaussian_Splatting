import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from skate4d.replays import slider_center, passage_boundaries, fit_passage


class ReplayTests(unittest.TestCase):
    def test_slider_local_contrast(self):
        pixels=bytearray([150]*(100*16))
        for y in range(4,12):
            for x in range(30,54):
                pixels[y*100+x]=230
        self.assertEqual(slider_center(pixels,100,16),41.5)
        self.assertIsNone(slider_center(bytes([230]*(100*16)),100,16))

    def test_resets_skip_missing(self):
        self.assertEqual(passage_boundaries([150,300,500,None,150,300,500]),[0,4,7])

    def test_linear_fit_with_pause_and_outlier(self):
        trace=[150]*10+[150+3*i for i in range(130)]
        trace[55]=None
        trace[65]=400
        fit=fit_passage(trace,0,len(trace),195,495,30)
        self.assertEqual(fit['first_frame'],25)
        self.assertEqual(fit['end_frame_exclusive'],125)
        self.assertAlmostEqual(fit['pixels_per_second'],90)

    def test_incomplete_pass_rejected(self):
        with self.assertRaises(ValueError):
            fit_passage([150+3*i for i in range(50)],0,50,195,495,30)


if __name__=='__main__':
    unittest.main()
