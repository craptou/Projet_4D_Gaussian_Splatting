"""Run the bounded DyNeRF GPU test from Windows through Ubuntu WSL2.

Usage after setup: .venv\Scripts\python.exe scripts/run_local_reference.py
Compilation uses the Linux filesystem; data and results stay in this repository.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time
from live_process import live_run


def logged(command, destination, cwd=None, timeout=1200):
    labels = {"depth-diff-gaussian-rasterization": "Compilation du rasteriseur CUDA (premiere fois : 1-10 min)",
        "simple-knn": "Compilation simple-knn (premiere fois : 1-5 min)",
        "loader": "Verification des images, cameras et timestamps",
        "training": "ENTRAINEMENT GPU : 2 etapes coarse + 10 fine (estimation : 1-5 min)",
        "rendering": "RENDU de 30 images reservees (estimation : 1-5 min)"}
    live_run(command, destination, labels.get(destination.stem, destination.stem), cwd, timeout)


def windows(root, source, output, quality=False):
    if not source.exists():
        subprocess.run([sys.executable, root / "scripts/prepare_local_reference.py",
                        "--output", source], check=True, cwd=root)
    def linux_path(path):
        return subprocess.check_output(["wsl", "-d", "Ubuntu-22.04", "-u", "root",
            "--exec", "wslpath", "-a", "-u", str(path)], encoding="utf-8").strip()
    copy = """set -euo pipefail
src="$1"
dest=/root/skate4d/project
mkdir -p "$dest"
tar -C "$src" --exclude=.git --exclude=__pycache__ --exclude=build --exclude='*.pyc' -cf - configs environment scripts src pyproject.toml docs/evidence/dynerf-reference-init.npz third_party/4DGaussians | tar -C "$dest" -xf -
"""
    subprocess.run(["wsl", "-d", "Ubuntu-22.04", "-u", "root", "--exec", "/bin/bash",
                    "-s", "--", linux_path(root)], input=copy.encode(), check=True)
    command = ["wsl", "-d", "Ubuntu-22.04", "-u", "root", "--exec", "/opt/skate4d/venv/bin/python",
        "/root/skate4d/project/scripts/run_local_reference.py", "--source", linux_path(source),
        "--output", linux_path(output)]
    if quality:
        command.append("--quality")
    subprocess.run(command, check=True)


def linux(root, source, output, quality=False):
    upstream = root / "third_party/4DGaussians"
    model = output / "model"
    if model.exists():
        raise ValueError("Model output exists; choose a fresh --output directory")
    if not (source / "preparation.json").exists():
        raise ValueError("Run prepare_local_reference.py first")
    os.environ.update(CUDA_HOME="/usr/local/cuda-12.1", TORCH_CUDA_ARCH_LIST="8.9", MAX_JOBS="2",
                      PYTHONUNBUFFERED="1", COLUMNS="120", LINES="40")
    os.environ["PATH"] = "/usr/local/cuda-12.1/bin:" + os.environ["PATH"]
    import torch
    assert torch.cuda.is_available() and torch.version.cuda == "12.1"
    assert torch.cuda.get_device_capability() == (8, 9), "This local configuration targets the RTX 4050"
    assert torch.arange(10, device="cuda").sum().item() == 45
    logs = output / "logs"
    for folder, module in [("depth-diff-gaussian-rasterization", "diff_gaussian_rasterization"),
                           ("simple-knn", "simple_knn._C")]:
        check = subprocess.run([sys.executable, "-c", "import " + module], capture_output=True)
        if check.returncode:
            logged([sys.executable, "-m", "pip", "install", "--no-cache-dir", "--no-build-isolation",
                    "--no-deps", "-e", upstream / "submodules" / folder], logs / (folder + ".log"))
    logged([sys.executable, "-c", "import torch,diff_gaussian_rasterization,simple_knn._C; print('CUDA imports passed')"],
           logs / "extensions.log")
    logged([sys.executable, "-m", "pip", "freeze"], logs / "pip-freeze.log")
    loader_probe = """
import sys,json
from pathlib import Path
from scene.neural_3D_dataset_NDC import Neural3D_NDC_Dataset
train=Neural3D_NDC_Dataset(sys.argv[1],'train',1.0,eval_index=0)
test=Neural3D_NDC_Dataset(sys.argv[1],'test',1.0,eval_index=0)
assert len(train)==120 and len(test)==30
assert all('/cam00/' not in p for p in train.image_paths)
assert all('/cam00/' in p for p in test.image_paths)
assert tuple(test[29][0].shape)==(3,1014,1352)
assert abs(test[29][2]-29/300)<1e-7
Path(sys.argv[2]).write_text(json.dumps(dict(train_samples=len(train),test_samples=len(test),last_time=test[29][2],split='cam00 excluded from training'),indent=2))
print('Actual upstream loader: split, dimensions, sample counts and timestamps passed')
"""
    logged([sys.executable, "-c", loader_probe, source, output / "loader.json"],
           logs / "loader.log", cwd=upstream)
    config = root / ("configs/experiments/dynerf-quality.py" if quality else "configs/experiments/dynerf-smoke.py")
    iterations = [1000, 3000] if quality else [10]
    start = time.monotonic()
    command = [sys.executable, "train.py", "-s", source, "--model_path", model, "--expname", "dynerf-local-reference",
            "--configs", config, "--save_iterations"] + [str(i) for i in iterations]
    command += ["--test_iterations"] + [str(i) for i in iterations] + ["--ip", "127.0.0.1"]
    if quality:
        if shutil.disk_usage(output).free < 6 * 2**30:
            raise OSError("Il faut au moins 6 Gio libres avant cet essai")
        live_run(command, logs / "training.log",
            "ENTRAINEMENT GPU : 200 coarse + 3000 fine; estimation initiale 15-35 min",
            cwd=upstream, timeout=5400, min_free_bytes=5 * 2**30)
    else:
        logged(command, logs / "training.log", cwd=upstream, timeout=600)
    training_seconds = time.monotonic() - start
    for name in ["point_cloud.ply", "deformation.pth"]:
        artifact = model / f"point_cloud/iteration_{iterations[-1]}" / name
        assert artifact.exists() and artifact.stat().st_size > 0, str(artifact)
    start = time.monotonic()
    for iteration in iterations:
        logged([sys.executable, "render.py", "--model_path", model, "--configs", config,
                "--iteration", str(iteration), "--skip_train", "--skip_video"],
                logs / f"rendering-{iteration}.log", cwd=upstream, timeout=600)
    rendering_seconds = time.monotonic() - start
    rendered = model / f"test/ours_{iterations[-1]}"
    from PIL import Image, ImageDraw
    assert len(list((rendered / "renders").glob("*.png"))) == 30
    assert len(list((rendered / "gt").glob("*.png"))) == 30
    sheet = Image.new("RGB", (1000, 3 * 402), "white")
    draw = ImageDraw.Draw(sheet)
    for row, index in enumerate([0, 14, 29]):
        for column, kind in enumerate(["gt", "renders"]):
            with Image.open(rendered / kind / f"{index:05d}.png") as image:
                assert image.size == (1352, 1014)
                sheet.paste(image.resize((500, 375)), (column * 500, row * 402 + 27))
            draw.text((column * 500 + 5, row * 402 + 7), f"cam00 frame {index} | {kind}", fill="black")
    sheet.save(output / "comparison.jpg", quality=90)
    preparation = json.loads((source / "preparation.json").read_text())
    result = dict(status=("Bounded quality pilot completed; convergence not established" if quality else "GPU execution gate passed; not a converged reconstruction"),
        torch=torch.__version__, torch_cuda=torch.version.cuda, gpu=torch.cuda.get_device_name(),
        gpu_memory_bytes=torch.cuda.get_device_properties(0).total_memory,
        coarse_steps=200 if quality else 2, fine_steps=iterations[-1], heldout_render_target_pairs=30,
        training_seconds=training_seconds, rendering_seconds=rendering_seconds,
        preparation=preparation, config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
        environment="Ubuntu 22.04 WSL2; native CUDA 12.1 compiler, PyTorch 2.1.2-cu121; compatibility port",
        limitations="Reduced cameras/time and sparse initialization; no full-scene reproduction, convergence or quality benchmark")
    if quality:
        from evaluate_quality_reference import evaluate
        result["validation_metrics"] = evaluate(output, source, iterations)
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--source", type=Path, default=root / "data/processed/dynerf-local-smoke")
    parser.add_argument("--output", type=Path, default=root / "outputs/dynerf-local-smoke")
    parser.add_argument("--quality", action="store_true")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if os.name == "nt":
        windows(root, source, output, args.quality)
    else:
        linux(root, source, output, args.quality)
