"""Live GPU viewer and two independent time/view demonstrations of the 4D model."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import threading
from urllib.parse import parse_qs, urlparse

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "third_party/4DGaussians"))
import imageio.v2 as imageio
import mmcv
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation, Slerp
import torch
from arguments import ModelParams, ModelHiddenParams, PipelineParams
from utils.params_utils import merge_hparams
from scene import Scene, GaussianModel
from scene.cameras import Camera
from gaussian_renderer import render


class ReferenceScene:
    def __init__(self, model):
        parser = argparse.ArgumentParser()
        lp = ModelParams(parser)
        hp = ModelHiddenParams(parser)
        pp = PipelineParams(parser)
        source = model.parents[2] / "data/processed/dynerf-local-quality"
        args = parser.parse_args(["-s", str(source), "-m", str(model)])
        args = merge_hparams(args, mmcv.Config.fromfile(str(root / "configs/experiments/dynerf-quality.py")))
        self.gaussians = GaussianModel(args.sh_degree, hp.extract(args))
        self.scene = Scene(lp.extract(args), self.gaussians, load_iteration=3000, shuffle=False)
        self.gaussians.active_sh_degree = 3  # Trained degree at fine step 3000.
        self.gaussians._deformation.eval()
        self.pipeline = pp.extract(args)
        self.background = torch.tensor([1, 1, 1] if args.white_background else [0, 0, 0], dtype=torch.float32, device="cuda")
        self.reference = self.scene.getTestCameras()[0]
        self.width, self.height = 768, 576
        self.blank = torch.zeros(3, self.height, self.width)
        train = self.scene.getTrainCameras()
        anchors = [train[i * 30] for i in range(4)]
        centers = [-camera.R @ camera.T for camera in anchors]
        left, right = max(((i, j) for i in range(4) for j in range(i+1, 4)),
                          key=lambda ij: np.linalg.norm(centers[ij[0]]-centers[ij[1]]))
        self.centers = [centers[left], centers[right]]
        self.rotations = Slerp([0, 1], Rotation.from_matrix(np.array([anchors[left].R, anchors[right].R])))
        names = ["cam01", "cam05", "cam12", "cam20"]
        self.view_names = [names[left], names[right]]
        self.lock = threading.Lock()

    @torch.no_grad()
    def frame(self, fraction, viewpoint=0.5, reference=True):
        fraction = float(fraction)
        viewpoint = float(viewpoint)
        if not np.isfinite([fraction, viewpoint]).all() or not (0 <= fraction <= 1 and 0 <= viewpoint <= 1):
            raise ValueError("Time and viewpoint must be finite values in [0,1]")
        if reference:
            rotation, translation = self.reference.R, self.reference.T
        else:
            rotation = self.rotations(viewpoint).as_matrix()
            center = (1-viewpoint)*self.centers[0] + viewpoint*self.centers[1]
            translation = -rotation.T @ center
        camera = Camera(colmap_id=0, R=rotation, T=translation,
            FoVx=self.reference.FoVx, FoVy=self.reference.FoVy, image=self.blank,
            gt_alpha_mask=None, image_name="4d-preview", uid=0, time=fraction*29/300)
        with self.lock:
            image = render(camera, self.gaussians, self.pipeline, self.background,
                           stage="fine", cam_type=self.scene.dataset_type)["render"].clamp(0, 1)
            return (image.permute(1, 2, 0).cpu().numpy()*255 + 0.5).astype(np.uint8)

    @torch.no_grad()
    def diagnostics(self):
        g = self.gaussians
        def points(t):
            times = torch.full((len(g._xyz), 1), t, dtype=g._xyz.dtype, device="cuda")
            return g._deformation(g._xyz, g._scaling, g._rotation, g._opacity, g.get_features, times)[0]
        displacement = torch.linalg.vector_norm(points(29/300)-points(0), dim=1).cpu().numpy()
        a, b = self.frame(0), self.frame(1)
        left, right = self.frame(14/29, 0, False), self.frame(14/29, 1, False)
        return dict(gaussians=len(g._xyz), source_frames=30, learned_duration_seconds=29/30,
            model_time_range=[0, 29/300], camera_path=self.view_names,
            camera_centers=[c.tolist() for c in self.centers],
            center_displacement_scene_units=dict(median=float(np.median(displacement)),
                p95=float(np.percentile(displacement, 95)), maximum=float(displacement.max())),
            fixed_camera_time_pixel_mae=float(np.abs(a.astype(float)-b).mean()),
            fixed_time_view_pixel_mae=float(np.abs(left.astype(float)-right).mean()),
            limitations="Learned deformations, not verified physical tracks. Front-facing interpolated views; no 360-degree reconstruction.")


def export(scene, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, frames, fps in [
        ("time", ((i/29, 0.5, True) for i in range(30)), 10),
        ("view", ((14/29, 1-abs(2*i/59-1), False) for i in range(60)), 15)]:
        with imageio.get_writer(str(output/f"4d-demo-{name}.mp4"), fps=fps, codec="libx264", quality=8) as writer:
            for index, (t, v, fixed) in enumerate(frames):
                writer.append_data(scene.frame(t, v, fixed))
                if index % 10 == 0:
                    print(f"Export {name}: {index} images", flush=True)
    report = scene.diagnostics()
    report["clips"] = {"time": "cam00 fixed, source frames 0..29 at 3x slow motion",
                       "view": "time fixed at source frame 14; camera translation + SLERP between calibrated endpoints"}
    (output/"demonstration.json").write_text(json.dumps(report, indent=2)+"\n")
    Image.fromarray(scene.frame(14/29, .5, False)).save(output/"novel-view.jpg", quality=92)
    print(json.dumps(report, indent=2), flush=True)


def serve(scene, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, data, kind, status=200):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self.send((root/"viewer/reference4d.html").read_bytes(), "text/html; charset=utf-8")
            elif parsed.path == "/meta":
                self.send(json.dumps(dict(application="skate4d-live-reference", frames=30,
                    seconds=29/30, views=scene.view_names, rendering="live GPU 4D Gaussian model")).encode(), "application/json")
            elif parsed.path == "/render":
                try:
                    query = parse_qs(parsed.query)
                    image = scene.frame(float(query.get("time", [.5])[0]),
                        float(query.get("view", [.5])[0]), query.get("mode", ["reference"])[0] == "reference")
                    buffer = io.BytesIO()
                    Image.fromarray(image).save(buffer, format="JPEG", quality=88)
                    self.send(buffer.getvalue(), "image/jpeg")
                except (ValueError, TypeError) as error:
                    self.send(str(error).encode(), "text/plain", 400)
            else:
                self.send(b"Not found", "text/plain", 404)

        def do_POST(self):
            if self.path != "/stop":
                self.send(b"Not found", "text/plain", 404)
                return
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).hostname not in {"127.0.0.1", "localhost"}:
                self.send(b"Forbidden", "text/plain", 403)
                return
            self.send(b"Stopped", "text/plain")
            threading.Thread(target=server.shutdown, daemon=True).start()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"READY http://127.0.0.1:{port} — live 4D GPU rendering", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()
    print("Loading 4D Gaussian scene on GPU...", flush=True)
    scene = ReferenceScene(args.model)
    if args.export:
        export(scene, args.export)
    else:
        serve(scene, args.port)
