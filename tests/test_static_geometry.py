"""Known geometry and global-feasibility guards for the static diagnostic."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import ModuleType

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


class StaticGeometryTests(unittest.TestCase):
    def test_static_renderer_bypasses_deformation_for_fine_calls(self):
        from fixed_static_scene import instrument_static_render
        stub=ModuleType('gaussian_renderer')
        stub.render=lambda *args,**kwargs:kwargs['stage']
        stub.network_gui=object()
        namespace={}
        with patch.dict(sys.modules,{'gaussian_renderer':stub}):
            exec(instrument_static_render('from gaussian_renderer import render, network_gui'),namespace)
            self.assertEqual(namespace['render'](stage='fine'),'coarse')
        with self.assertRaises(ValueError):instrument_static_render('incompatible import')

    def test_projection_triangulation_recovers_known_point(self):
        import numpy as np
        from static_board_geometry import project,triangulate_centers
        poses=[np.c_[np.eye(3),[0,0,0]],np.c_[np.eye(3),[-1,0,0]]]
        point=np.array([[.3,.2,4.]])
        pixels=[project(point,p,[100,50,50])[0][0] for p in poses]
        np.testing.assert_allclose(triangulate_centers(pixels,poses,[100,50,50]),point[0],atol=1e-10)

    def test_largest_component_uses_diagonal_connectivity(self):
        import numpy as np
        from static_board_geometry import largest_component
        mask=np.zeros((8,8),bool)
        mask[0,0]=True;mask[1,1]=True;mask[2,2]=True;mask[7,7]=True
        selected=largest_component(mask)
        self.assertEqual(int(selected.sum()),3)
        self.assertFalse(selected[7,7])


@unittest.skipUnless(importlib.util.find_spec('scipy'),'WSL scientific environment supplies scipy')
class GlobalBoxTests(unittest.TestCase):
    def test_consistent_boxes_feasible(self):
        import numpy as np
        from check_static_boxes import feasible
        records=[dict(camera_id='a',world_to_camera=np.c_[np.eye(3),[0,0,0]].tolist()),
                 dict(camera_id='b',world_to_camera=np.c_[np.eye(3),[-1,0,0]].tolist())]
        result=feasible(records,{'a':[48,48,52,52],'b':[28,48,32,52]},[100,50,50])
        self.assertTrue(result['feasible'])

    def test_incompatible_boxes_rejected_without_finite_search_cube(self):
        import numpy as np
        from check_static_boxes import feasible
        records=[dict(camera_id=n,world_to_camera=np.c_[np.eye(3),[0,0,0]].tolist()) for n in ['a','b']]
        self.assertFalse(feasible(records,{'a':[10,10,20,20],'b':[40,40,50,50]},[100,50,50])['feasible'])


if __name__=='__main__':unittest.main()
