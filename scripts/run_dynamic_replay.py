"""Progress-reporting launcher for the isolated Dynamic3DGaussians GPU pilot."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import json
import time
from live_process import live_run


def run(source,output,initial=2000,subsequent=400):
    root=Path(__file__).resolve().parents[1]
    if os.name=='nt':
        def linux(path):return subprocess.check_output(['wsl','-d','Ubuntu-22.04','-u','root','--exec','wslpath','-a','-u',str(path)],encoding='utf-8').strip()
        subprocess.run(['wsl','-d','Ubuntu-22.04','-u','root','--exec','/opt/skate4d/dynamic-venv/bin/python',linux(Path(__file__).resolve()),
            '--source',linux(source),'--output',linux(output),'--initial-steps',str(initial),'--subsequent-steps',str(subsequent)],check=True)
        return
    os.environ.update(OMP_NUM_THREADS='4',PYTHONUNBUFFERED='1')
    if output.exists():raise ValueError('Choose fresh output')
    # Logs outside the model directory so the engine can enforce fresh output.
    logs=output.parent/(output.name+'-logs')
    timings={}
    for phase in ['train','render']:
        started=time.monotonic()
        live_run([sys.executable,root/'scripts/dynamic_replay_engine.py',phase,'--source',source,'--output',output,
            '--initial-steps',str(initial),'--subsequent-steps',str(subsequent)],logs/(phase+'.log'),
            'Dynamic3DGaussians '+phase,cwd=root,timeout=2400 if phase=='train' else 300,min_free_bytes=5*2**30)
        timings[phase]=time.monotonic()-started
    (output/'launcher.json').write_text(json.dumps(dict(wall_seconds=timings),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-dense-comparison'))
    p.add_argument('--output',type=Path,default=Path('outputs/dynamic-comparison/gpu'))
    p.add_argument('--initial-steps',type=int,default=2000);p.add_argument('--subsequent-steps',type=int,default=400)
    a=p.parse_args();run(a.source.resolve(),a.output.resolve(),a.initial_steps,a.subsequent_steps)
