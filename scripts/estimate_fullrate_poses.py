"""Localize every training frame against the frozen sampled SfM map on CPU.

No interpolation, holdout frames, retriangulation, or modification of the input map.
Per-passage checkpoints support resume with identical source/config fingerprints.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from fractions import Fraction
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import threading
import time
import numpy as np
from PIL import Image
import pycolmap
import _bootstrap
from skate4d.dataset import ROOT
from skate4d.localization import accepted,pose_quality,unique_correspondences


def write_json(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(tmp,path)


def fingerprint(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle,'sha256').hexdigest()


class Localizer:
    def __init__(self,reference,dataset,feature_limit=2048):
        self.reference=reference
        self.feature_limit=feature_limit
        self.meta=json.loads((dataset/'manifest.json').read_text(encoding='utf-8'))
        self.config=self.meta['config']
        self.cuts=json.loads((ROOT/self.config['cuts']).read_text(encoding='utf-8'))
        self.source=ROOT/self.config['source']
        self.model=pycolmap.Reconstruction(reference/'sparse/0')
        self.camera=next(iter(self.model.cameras.values()))
        if self.camera.model_name!='SIMPLE_PINHOLE':
            raise ValueError('This pilot localizer requires the existing SIMPLE_PINHOLE model')
        if len(self.model.cameras)!=1:
            raise ValueError('Expected shared frozen intrinsics')
        self.mask=np.asarray(Image.open(dataset/'background-mask.png'))
        self.width,self.height=self.camera.width,self.camera.height
        if self.mask.shape!=(self.height,self.width):
            raise ValueError('Background mask dimensions differ from intrinsics')
        self.points={int(k):np.asarray(v.xyz).copy() for k,v in self.model.points3D.items()}
        self.anchors={}
        with pycolmap.Database.open(reference/'database.db') as db:
            for image in self.model.images.values():
                passage=image.name.split('/')[0]
                if passage==self.config['reserved_holdout'] or passage not in self.config['training_passages']:
                    raise ValueError('Unexpected or held-out image in reference model')
                ids={i:int(p.point3D_id) for i,p in enumerate(image.points2D) if p.has_point3D()}
                anchor=dict(name=image.name,index=int(Path(image.name).stem.split('_')[-1])-1,
                    descriptors=db.read_descriptors(image.image_id),point_ids=ids,
                    matrix=image.cam_from_world().matrix().copy())
                self.anchors.setdefault(passage,[]).append(anchor)
        self.local=threading.local()

    def tools(self):
        if not hasattr(self.local,'extractor'):
            options=pycolmap.FeatureExtractionOptions(num_threads=1,max_image_size=1000)
            options.sift.max_num_features=self.feature_limit
            self.local.extractor=pycolmap.FeatureExtractor.create(options,pycolmap.Device.cpu)
            self.local.matcher=pycolmap.FeatureMatcher.create(pycolmap.FeatureMatchingOptions(num_threads=1),pycolmap.Device.cpu)
            self.local.camera=pycolmap.Camera(model='SIMPLE_PINHOLE',width=self.width,height=self.height,
                                             params=self.camera.params.copy())
        return self.local.extractor,self.local.matcher,self.local.camera

    def solve(self,rgb,passage,index,native_gray=False,expanded_refs=False,include_support=False):
        extractor,matcher,camera=self.tools()
        # CPU SIFT needs a grayscale bitmap even though the wrapper accepts RGB arrays.
        gray=(np.asarray(pycolmap.Bitmap.from_array(rgb).clone_as_grey().to_array()) if native_gray
              else np.asarray(Image.fromarray(rgb).convert('L')))
        keypoints,descriptors=extractor.extract_from_uint8_array(gray)
        xy=np.asarray([[p.x,p.y] for p in keypoints],dtype=float).reshape(-1,2)
        keep=np.array([i for i,(x,y) in enumerate(xy)
            if 0<=x<self.width and 0<=y<self.height and self.mask[int(y),int(x)]>0],dtype=int)
        xy=xy[keep]
        query=pycolmap.FeatureDescriptors(descriptors.type,descriptors.data[keep])
        refs=sorted(self.anchors[passage],key=lambda a:abs(a['index']-index))
        votes={};tried=[];last=None
        # Try nearest temporal anchors first, then the rest, then neighboring passages.
        neighbors=sorted((n for n in self.anchors if n!=passage),key=lambda n:abs(int(n[3:])-int(passage[3:])))[:2]
        extra=[min(self.anchors[n],key=lambda a:abs(a['index']-index)) for n in neighbors]
        if expanded_refs:
            # Retrieval uses an actual neighboring anchor only; it does not supply
            # or interpolate the query pose used in the PnP estimate.
            base=refs[0]['matrix'];center=-base[:,:3].T@base[:,3]
            def proximity(anchor):
                m=anchor['matrix'];c=-m[:,:3].T@m[:,3]
                angle=np.degrees(np.arccos(np.clip((np.trace(m[:,:3]@base[:,:3].T)-1)/2,-1,1)))
                return angle+5*np.linalg.norm(c-center)
            other=[a for n,items in self.anchors.items() if n!=passage for a in items]
            extra=sorted(other,key=proximity)[:20]
        for number,anchor in enumerate(refs+extra,1):
            matches=matcher.match(pycolmap.FeatureKeypoints(),query,pycolmap.FeatureKeypoints(),anchor['descriptors'])
            tried.append(anchor['name'])
            for q,r in matches:
                point=anchor['point_ids'].get(int(r))
                if point is not None:
                    votes.setdefault(int(q),set()).add(point)
            if number<2 or (number<len(refs) and number not in [2,4]):
                continue
            pairs=unique_correspondences(votes)
            if len(pairs)<30:
                continue
            p2=np.array([xy[q] for q,p in pairs])
            p3=np.array([self.points[p] for q,p in pairs])
            estimation=pycolmap.AbsolutePoseEstimationOptions()
            estimation.ransac.max_error=4
            estimation.ransac.random_seed=0
            result=pycolmap.estimate_and_refine_absolute_pose(p2,p3,camera,estimation,
                pycolmap.AbsolutePoseRefinementOptions(refine_focal_length=False,refine_extra_params=False))
            if result is None:
                continue
            matrix=result['cam_from_world'].matrix()
            quality=pose_quality(p2,p3,matrix,result['inlier_mask'],self.camera.params)
            last=quality
            if accepted(quality):
                accepted_result=dict(status='localized',method='fixed_map_sift_pnp_ransac',
                    world_to_camera=matrix.tolist(),center_world=(-matrix[:,:3].T@matrix[:,3]).tolist(),
                    quality=quality,reference_images=tried)
                if include_support:
                    accepted_result['_support']=dict(descriptors=query,
                        point_ids={int(pairs[j][0]):int(pairs[j][1]) for j,ok in enumerate(result['inlier_mask']) if ok})
                return accepted_result
        return dict(status='failed',method='fixed_map_sift_pnp_ransac',quality=last,
                    reference_images=tried,reason='Insufficient accepted 2D-3D support; no interpolated substitute')

    def passage(self,name,out):
        first=next(c['first_frame'] for c in self.cuts['candidates'] if c['id']==name)
        count=self.cuts['frames_per_clip'];fps=float(Fraction(self.cuts['fps']))
        x,y,w,h=self.config['crop_xywh']
        decoded=subprocess.run(['ffmpeg','-nostdin','-v','error','-ss',f'{first/fps:.9f}',
            '-i',str(self.source),'-vf',f'crop={w}:{h}:{x}:{y}','-frames:v',str(count),
            '-fps_mode','passthrough','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],
            capture_output=True,check=True).stdout
        if len(decoded)!=count*w*h*3:
            raise ValueError(f'Unexpected decoded size in {name}')
        video=np.frombuffer(decoded,np.uint8).reshape(count,h,w,3)
        anchors={a['index']:a for a in self.anchors[name]}
        rows=[]
        for i,rgb in enumerate(video):
            row=dict(image_path=f'{name}/frame_{i+1:05d}.png',camera_id=name,clip_frame_index=i,
                source_frame_index=first+i,time_seconds=i/fps,time_normalized=i/count,split='train')
            if i in anchors:
                m=anchors[i]['matrix']
                result=dict(status='localized',method='inherited_sparse_anchor',world_to_camera=m.tolist(),
                    center_world=(-m[:,:3].T@m[:,3]).tolist())
            else:
                result=self.solve(rgb,name,i)
            rows.append(dict(**row,**result))
        write_json(out/f'{name}.json',dict(camera_id=name,frames=rows))
        success=sum(r['status']=='localized' for r in rows)
        return name,success,len(rows)


_WORKER=None


def initialize_worker(reference,dataset,database_lock):
    global _WORKER
    # Database.open performs SQLite initialization even for descriptor reads.
    # Serialize this short load to avoid factory-level startup write locks.
    with database_lock:
        _WORKER=Localizer(reference,dataset)


def localize_passage(name,parts):
    return _WORKER.passage(name,parts)


def run(reference,dataset,output,workers,resume):
    start=time.monotonic()
    if workers<1 or workers>8:
        raise ValueError('Use 1 to 8 CPU workers')
    localizer=Localizer(reference,dataset)
    config=dict(reference=str(reference.relative_to(ROOT)) if reference.is_relative_to(ROOT) else str(reference),
        dataset=str(dataset),source_sha256=fingerprint(localizer.source),
        map_sha256=fingerprint(reference/'sparse/0/points3D.bin'),
        images_sha256=fingerprint(reference/'sparse/0/images.bin'),
        cameras_sha256=fingerprint(reference/'sparse/0/cameras.bin'),
        cuts_sha256=fingerprint(ROOT/localizer.config['cuts']),
        manifest_sha256=fingerprint(dataset/'manifest.json'),
        mask_sha256=fingerprint(dataset/'background-mask.png'),config=localizer.config,
        workers=workers,pycolmap_version=pycolmap.__version__,max_ransac_error_px=4,
        min_inliers=30,min_inlier_ratio=.25,max_median_error_px=2,max_mean_error_px=3)
    if output.exists():
        if not resume:
            raise ValueError('Output exists; pass --resume only for this exact run')
        previous=json.loads((output/'run-config.json').read_text(encoding='utf-8'))
        if previous!=config:
            raise ValueError('Resume configuration/source/map fingerprint differs')
    else:
        output.mkdir(parents=True);write_json(output/'run-config.json',config)
    parts=output/'passages';parts.mkdir(exist_ok=True)
    pending=[]
    for name in localizer.config['training_passages']:
        if not (parts/f'{name}.json').exists():
            pending.append(name)
    if not pending and (output/'report.json').exists():
        print('All passage checkpoints and final report already exist; preserved without rewriting timing.',flush=True)
        return
    print(f'CPU localization: {len(pending)} passages, {workers} workers; cam07 excluded',flush=True)
    # The installed bindings serialize costly SIFT calls across Python threads.
    # Independent processes permit real CPU parallelism and independent native state.
    context=multiprocessing.get_context('spawn')
    database_lock=context.Lock()
    with ProcessPoolExecutor(max_workers=workers,mp_context=context,initializer=initialize_worker,
                             initargs=(reference,dataset,database_lock)) as pool:
        futures=[pool.submit(localize_passage,n,parts) for n in pending]
        for future in as_completed(futures):
            name,success,count=future.result()
            print(f'{name}: {success}/{count} poses; elapsed {time.monotonic()-start:.1f}s',flush=True)
    rows=[]
    for name in localizer.config['training_passages']:
        rows.extend(json.loads((parts/f'{name}.json').read_text(encoding='utf-8'))['frames'])
    query=[r for r in rows if r['method']!='inherited_sparse_anchor']
    good=[r for r in query if r['status']=='localized']
    errors=[r['quality']['mean_error_px'] for r in good]
    result=dict(total_frames=len(rows),localized_frames=sum(r['status']=='localized' for r in rows),
        inherited_anchors=len(rows)-len(query),new_localized_frames=len(good),failed_frames=len(query)-len(good),
        per_passage={n:sum(r['status']=='localized' for r in rows if r['camera_id']==n) for n in localizer.config['training_passages']},
        pnp_frame_mean_error_average_px=float(np.mean(errors)) if errors else None,
        pnp_frame_mean_error_p95_px=float(np.quantile(errors,.95)) if errors else None,
        elapsed_seconds=time.monotonic()-start,holdout=localizer.config['reserved_holdout'],holdout_used=False,
        method='Frozen sparse background, shared fixed intrinsics, per-frame SIFT 2D-3D localization; no interpolation',
        failed_images=[r['image_path'] for r in rows if r['status']=='failed'])
    write_json(output/'poses.json',dict(camera=dict(model=localizer.camera.model_name,width=localizer.width,
        height=localizer.height,params=localizer.camera.params.tolist()),frames=rows))
    write_json(output/'report.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,default=ROOT/'outputs/replay-pose-expanded')
    p.add_argument('--dataset',type=Path,default=ROOT/'data/processed/replay-pose-expanded')
    p.add_argument('--output',type=Path,default=ROOT/'outputs/replay-fullrate-poses')
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--resume',action='store_true')
    args=p.parse_args()
    try:
        run(args.reference.resolve(),args.dataset.resolve(),args.output.resolve(),args.workers,args.resume)
    except (ValueError,OSError,RuntimeError,subprocess.CalledProcessError) as error:
        p.exit(1,f'ERROR: {error}\nSource map unchanged; completed passage checkpoints retained.\n')
