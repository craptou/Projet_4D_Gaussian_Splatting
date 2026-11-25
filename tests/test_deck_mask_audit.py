"""Guard annotation coordinate conventions and overlap calculations."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


class DeckMaskAuditTests(unittest.TestCase):
    def test_polygon_uses_image_xy_not_array_yx(self):
        import numpy as np
        from audit_deck_masks import polygon_mask
        mask=polygon_mask([[1,2],[4,2],[4,3],[1,3]],[8,6])
        self.assertEqual(mask.shape,(6,8))
        self.assertEqual(int(mask.sum()),8)
        self.assertTrue(mask[2,4]);self.assertFalse(mask[4,2])

    def test_bad_coordinates_rejected(self):
        from audit_deck_masks import polygon_mask
        for polygon in [[[0,0],[8,0],[0,2]],[[-1,0],[2,0],[0,2]],[[0,0],[float('nan'),1],[2,2]]]:
            with self.assertRaises(ValueError):polygon_mask(polygon,[8,6])

    def test_iou_and_empty_union_guard(self):
        import numpy as np
        from audit_deck_masks import iou
        a=np.array([[True,False],[False,False]])
        b=np.array([[True,True],[False,False]])
        self.assertEqual(iou(a,b),.5)
        self.assertEqual(iou(a,a),1.)
        with self.assertRaises(ValueError):iou(np.zeros((2,2),bool),np.zeros((2,2),bool))


if __name__=='__main__':unittest.main()
