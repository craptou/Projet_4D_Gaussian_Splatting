"""Temporal spacing and split guards for the joint replay preparation."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


class JointReplayTests(unittest.TestCase):
    def test_physical_spacing_is_not_replaced_by_uniform_indices(self):
        from prepare_joint_replay import normalized_times
        actual=normalized_times([-.85,-.60,-.40])
        self.assertEqual(actual[0],0.);self.assertEqual(actual[2],1.)
        self.assertAlmostEqual(actual[1],5/9)
        self.assertNotEqual(actual[1],.5)

    def test_invalid_physical_times_rejected(self):
        from prepare_joint_replay import normalized_times
        for times in [[0,0,1],[0,2,1],[0,float('nan'),1]]:
            with self.assertRaises(ValueError):normalized_times(times)

    def test_reserved_view_seed_leakage_rejected_before_staging(self):
        from prepare_joint_replay import prepare
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);sources=[]
            for i in range(3):
                p=root/str(i);p.mkdir();sources.append(p)
                (p/'manifest.json').write_text('{}')
                (p/'preparation.json').write_text(json.dumps({'heldout_used_for_seeds':i==0}))
            with self.assertRaisesRegex(ValueError,'leakage'):prepare(sources,root/'output')
            self.assertFalse((root/'output').exists())


if __name__=='__main__':unittest.main()
