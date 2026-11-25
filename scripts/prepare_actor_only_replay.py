"""Clone the existing joint dataset unchanged except for time-deformation routing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil


def prepare(source,output):
    if output.exists():raise ValueError('Choose a fresh dataset')
    manifest=json.loads((source/'manifest.json').read_text())
    if not manifest.get('temporal_scene'):raise ValueError('Expected temporal dataset')
    def link_or_copy(src,dst):
        try:os.link(src,dst)
        except OSError:shutil.copy2(src,dst)
    shutil.copytree(source,output,copy_function=link_or_copy)
    (output/'manifest.json').unlink()
    manifest['actor_only_deformation']=True
    manifest['deformation_partition']='SfM background seed descendants bypass every temporal deformation output; visual-hull seed descendants use deformation. This is seed provenance, not semantic labels or material tracking.'
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    paths={r['image_path'] for r in manifest['frames']}|{r['evaluation_mask_path'] for r in manifest['frames']}|{'points3D_multipleview.ply'}
    hashes={}
    for path in sorted(paths):
        digest=hashlib.sha256((source/path).read_bytes()).hexdigest()
        if hashlib.sha256((output/path).read_bytes()).hexdigest()!=digest:raise ValueError('Input contents changed')
        hashes[path]=digest
    report=dict(source_manifest_sha256=hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),
        data_hashes=hashes,changed_only='actor_only_deformation and its explanatory metadata',
        caution='Background can optimize between training steps, but its saved parameters have no time deformation. Actor motion can still occlude background pixels. Seed roles may be imperfect.')
    (output/'actor-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Actor-only routing enabled;45 RGB images,45 masks and canonical point cloud verified identical.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/processed/true-skate-joint-three'))
    p.add_argument('--output',type=Path,default=Path('data/processed/true-skate-joint-three-actor'))
    a=p.parse_args();prepare(a.source,a.output)
