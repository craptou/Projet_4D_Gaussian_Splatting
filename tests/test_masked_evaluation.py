"""Unavailable object regions must not become NaNs or invented quality scores."""
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


@unittest.skipUnless(importlib.util.find_spec('torch'),'WSL supplies torch')
class MaskedEvaluationTests(unittest.TestCase):
    def test_empty_or_tiny_masks_have_no_quality_score(self):
        import torch
        from masked_evaluation import region_metrics
        for pixels in [0,8,20]:
            mask=torch.zeros((6,6),dtype=torch.bool);mask.flatten()[:pixels]=True
            report=region_metrics(torch.ones(1,3,6,6),torch.zeros(1,3,6,6),mask)
            self.assertFalse(report['available']);self.assertIsNone(report['mean_psnr_db']);self.assertIsNone(report['mae'])

    def test_known_error_is_measured_only_inside_valid_mask(self):
        import torch
        from masked_evaluation import region_metrics
        mask=torch.zeros((6,6),dtype=torch.bool);mask[:5,:5]=True
        pred=torch.zeros(1,3,6,6);pred[:,:,mask]=1.
        report=region_metrics(pred,torch.zeros_like(pred),mask)
        self.assertTrue(report['available']);self.assertEqual(report['pixels'],25)
        self.assertEqual(report['mean_psnr_db'],0.);self.assertEqual(report['mae'],1.)

    def test_mismatched_coordinates_rejected(self):
        import torch
        from masked_evaluation import region_metrics
        with self.assertRaises(ValueError):region_metrics(torch.ones(1,3,6,6),torch.zeros(1,3,6,6),torch.ones(5,6,dtype=torch.bool))


if __name__=='__main__':unittest.main()
