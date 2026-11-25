"""All temporal attributes and gradient routes must respect the background partition."""
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fixed_actor_deformation import gate_outputs


@unittest.skipUnless(importlib.util.find_spec('torch'),'Torch supplied by WSL environment')
class ActorDeformationTests(unittest.TestCase):
    def test_all_attributes_static_and_actor_gradients(self):
        import torch
        base=[torch.ones(shape,requires_grad=True) for shape in [(4,3),(4,3),(4,4),(4,1),(4,16,3)]]
        offsets=[torch.full_like(value,2.,requires_grad=True) for value in base]
        mask=torch.tensor([False,True,False,True])
        output=gate_outputs(base,[a+b for a,b in zip(base,offsets)],mask)
        for original,result in zip(base,output):
            self.assertTrue(torch.equal(result[~mask],original[~mask]))
            self.assertTrue(torch.equal(result[mask],original[mask]+2))
        sum(value.sum() for value in output).backward()
        for original,offset in zip(base,offsets):
            self.assertTrue(torch.equal(original.grad,torch.ones_like(original)))
            self.assertTrue(torch.equal(offset.grad[~mask],torch.zeros_like(offset.grad[~mask])))
            self.assertTrue(torch.equal(offset.grad[mask],torch.ones_like(offset.grad[mask])))

    def test_invalid_partition_rejected(self):
        import torch
        values=[torch.ones(4,3)]*5
        for mask in [torch.ones(3,dtype=torch.bool),torch.ones(4),torch.ones(4,1,dtype=torch.bool)]:
            with self.assertRaises(ValueError):gate_outputs(values,values,mask)

    def test_upstream_clone_split_prune_preserve_parent_labels(self):
        import torch
        if not torch.cuda.is_available():self.skipTest('Upstream point operations require CUDA')
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'third_party/4DGaussians'))
        from scene.gaussian_model import GaussianModel
        model=GaussianModel.__new__(GaussianModel)
        model.setup_functions();model.percent_dense=1.
        tensors={'xyz':torch.zeros(2,3,device='cuda'),'f_dc':torch.zeros(2,1,3,device='cuda'),
            'f_rest':torch.zeros(2,15,3,device='cuda'),'opacity':torch.zeros(2,1,device='cuda'),
            'scaling':torch.zeros(2,3,device='cuda'),'rotation':torch.tensor([[1.,0,0,0]]*2,device='cuda')}
        attrs={'xyz':'_xyz','f_dc':'_features_dc','f_rest':'_features_rest','opacity':'_opacity','scaling':'_scaling','rotation':'_rotation'}
        groups=[]
        for name,value in tensors.items():
            param=torch.nn.Parameter(value);setattr(model,attrs[name],param)
            groups.append(dict(name=name,params=[param],lr=.001))
        model.optimizer=torch.optim.Adam(groups)
        model._deformation_table=torch.tensor([False,True],device='cuda')
        model.densify_and_clone(torch.ones(2,1,device='cuda'),.5,2.)
        self.assertEqual(model._deformation_table.tolist(),[False,True,False,True])
        model.densify_and_split(torch.tensor([[1.],[1.],[0.],[0.]],device='cuda'),.5,.5)
        self.assertEqual(model._deformation_table.tolist(),[False,True,False,True,False,True])
        model.prune_points(torch.tensor([True,False,False,False,False,False],device='cuda'))
        self.assertEqual(model._deformation_table.tolist(),[True,False,True,False,True])


if __name__=='__main__':unittest.main()
