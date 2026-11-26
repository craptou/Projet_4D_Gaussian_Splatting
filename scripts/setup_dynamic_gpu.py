"""Build a pinned Dynamic3DGaussians rasterizer without changing the working 4DGS environment."""
import json
import os
from pathlib import Path
import subprocess
import sys

PINS={'method':('https://github.com/JonathonLuiten/Dynamic3DGaussians.git','7dbbd4dec404308524ff402756bdb8143a2589b0','Dynamic3DGaussians'),
      'rasterizer':('https://github.com/JonathonLuiten/diff-gaussian-rasterization-w-depth.git','cb65e4b86bc3bd8ed42174b72a62e8d3a3a71110','dynamic-rasterizer')}


def setup():
    if os.name=='nt':
        path=subprocess.check_output(['wsl','-d','Ubuntu-22.04','-u','root','--exec','wslpath','-a','-u',str(Path(__file__).resolve())],encoding='utf-8').strip()
        subprocess.run(['wsl','-d','Ubuntu-22.04','-u','root','--exec','/opt/skate4d/venv/bin/python',path],check=True)
        return
    root=Path('/root/skate4d');base=Path('/opt/skate4d/venv');env=Path('/opt/skate4d/dynamic-venv')
    for url,commit,name in PINS.values():
        target=root/name
        if not target.exists():subprocess.run(['git','clone',url,str(target)],check=True)
        if subprocess.check_output(['git','-C',str(target),'status','--porcelain'],text=True).strip():raise ValueError('Refuse to change a modified checkout')
        subprocess.run(['git','-C',str(target),'checkout','--detach',commit],check=True)
        subprocess.run(['git','-C',str(target),'submodule','update','--init','--recursive'],check=True)
    if not (env/'bin/python').exists():subprocess.run([str(base/'bin/python'),'-m','venv',str(env)],check=True)
    site=env/'lib/python3.10/site-packages'
    (site/'shared-skate4d.pth').write_text(str(base/'lib/python3.10/site-packages')+'\n')
    os.environ.update(CUDA_HOME='/usr/local/cuda-12.1',TORCH_CUDA_ARCH_LIST='8.9',MAX_JOBS='1')
    os.environ['PATH']='/usr/local/cuda-12.1/bin:'+os.environ['PATH']
    marker=env/'dynamic-build.json'
    expected=dict(pins=PINS,base_environment=str(base),python='3.10',torch='2.1.2+cu121',architecture='8.9')
    # JSON roundtrip makes tuple/list comparison stable on repeat.
    expected=json.loads(json.dumps(expected))
    if not marker.exists() or json.loads(marker.read_text())!=expected:
        log=root/'dynamic-build.log'
        print('Building separate CUDA rasterizer; log: '+str(log),flush=True)
        with log.open('w') as out:
            subprocess.run([str(env/'bin/python'),'-m','pip','install','--no-build-isolation','--no-deps',str(root/'dynamic-rasterizer')],stdout=out,stderr=subprocess.STDOUT,check=True)
        marker.write_text(json.dumps(expected,indent=2)+'\n')
    subprocess.run([str(env/'bin/python'),'-c',"import torch,diff_gaussian_rasterization as r; print(torch.__version__,torch.cuda.get_device_name(),r.__file__); assert '/dynamic-venv/' in r.__file__"],check=True)
    print('Isolated Dynamic3DGaussians environment ready.',flush=True)


if __name__=='__main__':setup()
