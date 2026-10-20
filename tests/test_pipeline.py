"""Real FFmpeg smoke extraction plus failure and leakage regressions."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from extract_frames import extract
from make_dataset import stage
from skate4d.validation import validate
from skate4d.cameras import require_fixed


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.frames = self.base / "frames"
        self.frames.mkdir()
        self.meta = {"replay_id": "synthetic-test-only", "camera_motion": "fixed",
                     "camera_mode": "custom", "holdout_camera": "cam07"}
        self.write_meta()
        cameras = {}
        for cam in ("cam01", "cam02", "cam07"):
            (self.frames / cam).mkdir()
            for i in range(1, 4):
                Image.new("RGB", (64, 48), (i*50, 0, 0)).save(self.frames / cam / f"frame_{i:05d}.jpg")
            cameras[cam] = {"fps": "30", "resolution": [64, 48], "count": 3, "extracted_count": 3}
        (self.frames / "extraction.json").write_text(json.dumps({"source_frame_indices": [1, 2, 3], "cameras": cameras}))

    def write_meta(self):
        (self.frames / "metadata.json").write_text(json.dumps(self.meta))

    def test_valid(self):
        self.assertEqual(validate(self.frames)["frames_per_camera"], 3)

    def test_missing_frame(self):
        (self.frames / "cam01/frame_00002.jpg").unlink()
        with self.assertRaisesRegex(ValueError, "Missing"):
            validate(self.frames)

    def test_bad_name(self):
        (self.frames / "cam01/readme.txt").touch()
        with self.assertRaisesRegex(ValueError, "filename"):
            validate(self.frames)

    def test_resolution(self):
        Image.new("RGB", (32, 32)).save(self.frames / "cam01/frame_00001.jpg")
        with self.assertRaisesRegex(ValueError, "resolution"):
            validate(self.frames)

    def test_missing_holdout(self):
        self.meta["holdout_camera"] = "cam99"
        self.write_meta()
        with self.assertRaisesRegex(ValueError, "holdout"):
            validate(self.frames)

    def test_missing_motion(self):
        self.meta.pop("camera_motion")
        self.write_meta()
        with self.assertRaisesRegex(ValueError, "camera_motion"):
            validate(self.frames)

    def test_manifest_fps_mismatch(self):
        file = self.frames / "extraction.json"
        manifest = json.loads(file.read_text())
        manifest["cameras"]["cam02"]["fps"] = "24"
        file.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "FPS"):
            validate(self.frames)

    def test_manifest_count_mismatch(self):
        file = self.frames / "extraction.json"
        manifest = json.loads(file.read_text())
        manifest["cameras"]["cam02"]["extracted_count"] = 4
        file.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            validate(self.frames)

    def test_moving_rejected_at_stage(self):
        self.meta["camera_motion"] = "moving"
        self.write_meta()
        self.assertEqual(validate(self.frames)["camera_motion"], "moving")
        with self.assertRaisesRegex(ValueError, "MOVING_CAMERA"):
            stage(self.frames, self.base / "stage")

    def test_holdout_not_staged(self):
        target = self.base / "stage"
        mapping = stage(self.frames, target)
        self.assertEqual(mapping, {"cam01": "cam01", "cam02": "cam02"})
        self.assertFalse((target / "cam07").exists())
        with self.assertRaisesRegex(ValueError, "overwrite"):
            stage(self.frames, target)

    def test_contact_sheet(self):
        dest = self.base / "sheet.jpg"
        subprocess.run([sys.executable, ROOT / "scripts/inspect_frames.py", self.frames,
                        "--output", dest], check=True, capture_output=True)
        self.assertTrue(dest.is_file())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_real_extraction_interval_and_mismatch(self):
        raw = self.base / "raw"
        raw.mkdir()
        meta = dict(self.meta, fps=6, resolution=[64, 48])
        (raw / "metadata.json").write_text(json.dumps(meta))
        video = raw / "cam01.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                        "testsrc2=size=64x48:rate=6:duration=1", "-c:v", "libx264", video],
                       check=True, capture_output=True)
        for cam in ("cam02", "cam07"):
            shutil.copy2(video, raw / f"{cam}.mp4")
        out = self.base / "extracted"
        self.assertEqual(extract(raw, out, 2)["frames_per_camera"], 3)
        manifest = json.loads((out / "extraction.json").read_text())
        self.assertEqual(manifest["source_frame_indices"], [1, 3, 5])
        with self.assertRaisesRegex(ValueError, "already exists"):
            extract(raw, out)
        with self.assertRaisesRegex(ValueError, "positive"):
            extract(raw, self.base / "bad", 0)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=size=64x48:rate=5:duration=1", raw / "cam02.mp4"],
                       check=True, capture_output=True)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            extract(raw, self.base / "mismatched")
        self.assertFalse((self.base / "mismatched").exists())


if __name__ == "__main__":
    unittest.main()
