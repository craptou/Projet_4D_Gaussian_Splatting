"""Run the bounded True Skate experiment on the existing WSL2 GPU environment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from live_process import live_run


def run(root,source,output):
    if os.name=="nt":
        def linux(path):
            return subprocess.check_output(["wsl","-d","Ubuntu-22.04","-u","root","--exec","wslpath","-a","-u",str(path)],encoding="utf-8").strip()
        copy='''set -euo pipefail
src="$1"
dest=/root/skate4d/project
mkdir -p "$dest"
tar -C "$src" --exclude=.git --exclude=__pycache__ --exclude=build --exclude='*.pyc' -cf - configs scripts src pyproject.toml third_party/4DGaussians | tar -C "$dest" -xf -
'''
        subprocess.run(["wsl","-d","Ubuntu-22.04","-u","root","--exec","/bin/bash","-s","--",linux(root)],input=copy.encode(),check=True)
        subprocess.run(["wsl","-d","Ubuntu-22.04","-u","root","--exec","/opt/skate4d/venv/bin/python",
            "/root/skate4d/project/scripts/run_fixed_pilot.py","--source",linux(source),"--output",linux(output)],check=True)
        return
    if (output/"model").exists():
        raise ValueError("Model already exists; choose a fresh output")
    output.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(output).free<6*2**30:
        raise OSError("Need 6 GiB free before this bounded pilot")
    os.environ.update(CUDA_HOME="/usr/local/cuda-12.1",TORCH_CUDA_ARCH_LIST="8.9",MAX_JOBS="2",PYTHONUNBUFFERED="1",OMP_NUM_THREADS="4")
    os.environ["PATH"]="/usr/local/cuda-12.1/bin:"+os.environ["PATH"]
    import torch, diff_gaussian_rasterization, simple_knn._C
    assert torch.cuda.is_available()
    config=root/"configs/experiments/true-skate-fixed-pilot.py"
    command=[sys.executable,root/"scripts/fixed_pilot_engine.py"]
    shared=["--source",source,"--output",output,"--configs",config]
    times={}
    for phase,label,limit in [("probe","1/3 Verification du chargeur, des cameras et des projections",300),
        ("train","2/3 Entrainement True Skate : 200 coarse + 2000 fine (estimation 2-10 min)",1200),
        ("render","3/3 Rendu et evaluation de la camera reservee et de cam08",300)]:
        started=time.monotonic()
        live_run(command+[phase]+shared,output/"logs"/(phase+".log"),label,
            cwd=root/"third_party/4DGaussians",timeout=limit,min_free_bytes=5*2**30)
        times[phase]=time.monotonic()-started
    result=dict(status="Bounded True Skate pilot completed; inspect board quality separately",timing_seconds=times,
        gpu=torch.cuda.get_device_name(),coarse_steps=200,fine_steps=2000,
        config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
        loader=json.loads((output/"loader.json").read_text()),
        evaluation=json.loads((output/"evaluation-2000.json").read_text()))
    (output/"report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=Path("data/processed/true-skate-fixed-pilot-v2"))
    parser.add_argument("--output",type=Path,default=Path("outputs/true-skate-fixed-pilot"))
    args=parser.parse_args()
    run(Path(__file__).resolve().parents[1],args.source.resolve(),args.output.resolve())
