"""Regression guards for checkpoint scheduling and same-target comparisons."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from fixed_training_schedule import training_arguments


class ScheduleTests(unittest.TestCase):
    def test_all_duration_checkpoints_reach_upstream_cli(self):
        parser=argparse.ArgumentParser()
        parser.add_argument("--save_iterations",type=int,nargs="+")
        parser.add_argument("--test_iterations",type=int,nargs="+")
        command=training_arguments(Path("upstream"),Path("source"),Path("out"),Path("config"),[2000,5000,10000],[2000,5000,10000])
        args,_=parser.parse_known_args(command[1:])
        self.assertEqual(args.save_iterations,[2000,5000,10000])
        self.assertEqual(args.test_iterations,[2000,5000,10000])

    def test_old_pilot_schedule_still_supported(self):
        command=training_arguments(Path("upstream"),Path("source"),Path("out"),Path("config"),[500,2000],[2000])
        start=command.index("--save_iterations")+1
        end=command.index("--test_iterations")
        self.assertEqual(command[start:end],["500","2000"])

    def test_nonpositive_checkpoint_rejected(self):
        with self.assertRaises(ValueError):
            training_arguments(Path("upstream"),Path("source"),Path("out"),Path("config"),[0],[10000])


@unittest.skipUnless(importlib.util.find_spec("numpy"),"Install project SfM extras")
class DurationComparisonTests(unittest.TestCase):
    def test_mixed_targets_across_checkpoints_rejected(self):
        from PIL import Image
        from compare_fixed_duration import compare
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for iteration,color in [(2000,0),(5000,1),(10000,0)]:
                folder=root/f"renders-{iteration}/test-cam13/gt"
                folder.mkdir(parents=True)
                Image.new("RGB",(2,2),(color,0,0)).save(folder/"000.png")
                (root/f"evaluation-{iteration}.json").write_text(json.dumps({"metrics":{"test-cam13":{},"train-cam08":{}}}))
            with self.assertRaisesRegex(ValueError,"Targets differ"):
                compare(root,root/"comparison")
