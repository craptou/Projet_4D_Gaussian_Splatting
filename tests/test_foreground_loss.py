"""Check loss gradients, fail-closed instrumentation and training-only masks."""
import importlib.util
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fixed_foreground_loss import instrument_training


class InstrumentationTests(unittest.TestCase):
    def test_ambiguous_upstream_refused(self):
        anchor='Ll1 = l1_loss(image_tensor, gt_image_tensor[:,:3,:,:])'
        for text in ['',anchor+'\n'+anchor]:
            with self.assertRaises(ValueError):instrument_training(text)


@unittest.skipUnless(importlib.util.find_spec('torch'),'GPU environment supplies torch')
class ForegroundLossTests(unittest.TestCase):
    def test_mask_receives_larger_gradient_and_unmasked_batch_keeps_l1(self):
        import torch
        from fixed_foreground_loss import foreground_l1
        pred=torch.ones((2,3,2,2),requires_grad=True)
        target=torch.zeros_like(pred)
        mask=torch.tensor([[True,False],[False,False]])
        cams=[SimpleNamespace(mask=mask),SimpleNamespace(mask=None)]
        loss=foreground_l1(pred,target,cams,1.)
        self.assertAlmostEqual(loss.item(),1.5)
        loss.backward()
        self.assertGreater(pred.grad[0,0,0,0].item(),pred.grad[0,0,1,1].item())
        self.assertAlmostEqual(pred.grad[1,0,0,0].item(),1/24)
        plain=foreground_l1(pred,target,[SimpleNamespace(mask=None)]*2,1.)
        self.assertEqual(plain.item(),1.)

    def test_empty_or_wrong_shape_mask_rejected(self):
        import torch
        from fixed_foreground_loss import foreground_l1
        for mask in [torch.zeros(2,2,dtype=torch.bool),torch.ones(1,2,dtype=torch.bool)]:
            with self.assertRaises(ValueError):
                foreground_l1(torch.ones(1,3,2,2),torch.zeros(1,3,2,2),[SimpleNamespace(mask=mask)],1.)


if __name__=='__main__':unittest.main()
