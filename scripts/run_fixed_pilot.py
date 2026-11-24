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


def run(root,source,output,long=False):
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
        command=["wsl","-d","Ubuntu-22.04","-u","root","--exec","/opt/skate4d/venv/bin/python",
            "/root/skate4d/project/scripts/run_fixed_pilot.py","--source",linux(source),"--output",linux(output)]
        if long:command.append("--long")
        subprocess.run(command,check=True)
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
    config=root/("configs/experiments/true-skate-fixed-duration.py" if long else "configs/experiments/true-skate-fixed-pilot.py")
    iterations=[2000,5000,10000] if long else [2000]
    if long:
        import mmcv
        original=mmcv.Config.fromfile(str(root/"configs/experiments/true-skate-fixed-pilot.py")).to_dict()
        effective=mmcv.Config.fromfile(str(config)).to_dict()
        expected=json.loads(json.dumps(original))
        expected["OptimizationParams"]["iterations"]=10000
        if effective!=expected:
            raise ValueError("Duration control must change only OptimizationParams.iterations")
    command=[sys.executable,root/"scripts/fixed_pilot_engine.py"]
    shared=["--source",source,"--output",output,"--configs",config]
    times={}
    phases=[("probe","1/3 Verification du chargeur, des cameras et des projections",300,[]),
        ("train",f"2/3 Entrainement True Skate : 200 coarse + {iterations[-1]} fine",3600 if long else 1200,
            ["--save-iterations",*[str(i) for i in ([2000,5000,10000] if long else [500,2000])],
             "--test-iterations",*[str(i) for i in iterations]])]
    phases += [("render",f"3/3 Rendu et evaluation du checkpoint {i}",600,["--iteration",str(i)]) for i in iterations]
    for phase,label,limit,extra in phases:
        started=time.monotonic()
        key=f"render-{extra[-1]}" if phase=="render" and long else phase
        live_run(command+[phase]+shared+extra,output/"logs"/(key+".log"),label,
            cwd=root/"third_party/4DGaussians",timeout=limit,min_free_bytes=5*2**30)
        times[key]=time.monotonic()-started
    result=dict(status="Bounded True Skate pilot completed; inspect board quality separately",timing_seconds=times,
        gpu=torch.cuda.get_device_name(),coarse_steps=200,fine_steps=iterations[-1],
        config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
        loader=json.loads((output/"loader.json").read_text()),
        evaluation=json.loads((output/f"evaluation-{iterations[-1]}.json").read_text()))
    if long:
        result.update(checkpoints=iterations,effective_configuration=effective,
            evaluations={str(i):json.loads((output/f"evaluation-{i}.json").read_text()) for i in iterations})
    (output/"report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=Path("data/processed/true-skate-fixed-pilot-v2"))
    parser.add_argument("--output",type=Path,default=Path("outputs/true-skate-fixed-pilot"))
    parser.add_argument("--long",action="store_true",help="Original settings, 10000 fine steps and evaluations at 2000/5000/10000")
    args=parser.parse_args()
    run(Path(__file__).resolve().parents[1],args.source.resolve(),args.output.resolve(),args.long)
