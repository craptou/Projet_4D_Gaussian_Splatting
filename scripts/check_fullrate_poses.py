"""Audit full-rate localization coverage and motion, preserving per-frame failures."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import _bootstrap
from skate4d.dataset import ROOT


def audit(work):
    pose_file=work/'poses.json'
    poses=json.loads(pose_file.read_text(encoding='utf-8'))
    report=json.loads((work/'report.json').read_text(encoding='utf-8'))
    config=json.loads((work/'run-config.json').read_text(encoding='utf-8'))
    reference=ROOT/config['reference']
    for filename,key in [('points3D.bin','map_sha256'),('images.bin','images_sha256'),('cameras.bin','cameras_sha256')]:
        actual=hashlib.sha256((reference/'sparse/0'/filename).read_bytes()).hexdigest()
        if actual!=config[key]:
            raise ValueError(f'Reference map changed: {filename}')
    old=json.loads((reference/'poses-model-0.json').read_text(encoding='utf-8'))
    anchors={r['image_path']:np.array(r['world_to_camera']) for r in old['images']}
    by_passage={}
    for row in poses['frames']:
        if row['camera_id']==report['holdout'] or row['split']!='train':
            raise ValueError('Held-out/nontraining image present')
        by_passage.setdefault(row['camera_id'],[]).append(row)
    grid=[];translation=[];rotation=[];jumps=[]
    max_rotation_error=0.;max_center_error=0.;anchor_error=0.
    for name,rows in sorted(by_passage.items()):
        rows.sort(key=lambda r:r['clip_frame_index'])
        if [r['clip_frame_index'] for r in rows]!=list(range(109)):
            raise ValueError(f'Missing or repeated frame indices: {name}')
        states=[];tsteps=[];rsteps=[]
        for row in rows:
            state=0 if row['status']=='failed' else (2 if row['method']=='inherited_sparse_anchor' else 1)
            states.append(state)
            if not state:
                continue
            m=np.asarray(row['world_to_camera'])
            if m.shape!=(3,4) or not np.all(np.isfinite(m)):
                raise ValueError(f'Invalid pose: {row["image_path"]}')
            r=m[:,:3];center=np.asarray(row['center_world'])
            max_rotation_error=max(max_rotation_error,float(np.max(np.abs(r.T@r-np.eye(3)))))
            max_center_error=max(max_center_error,float(np.linalg.norm(center+r.T@m[:,3])))
            if row['method']=='inherited_sparse_anchor':
                anchor_error=max(anchor_error,float(np.max(np.abs(m-anchors[row['image_path']]))))
        for a,b in zip(rows,rows[1:]):
            if 'world_to_camera' not in a or 'world_to_camera' not in b:
                tsteps.append(float('nan'));rsteps.append(float('nan'));continue
            ra=np.array(a['world_to_camera'])[:,:3];rb=np.array(b['world_to_camera'])[:,:3]
            step=float(np.linalg.norm(np.array(b['center_world'])-a['center_world']))
            angle=float(np.degrees(np.arccos(np.clip((np.trace(rb@ra.T)-1)/2,-1,1))))
            tsteps.append(step);rsteps.append(angle)
            if step>.5 or angle>10:
                jumps.append(dict(camera_id=name,from_frame=a['clip_frame_index'],to_frame=b['clip_frame_index'],
                                  translation_step=step,rotation_step_deg=angle))
        grid.append(states);translation.append(tsteps);rotation.append(rsteps)
    if len(anchors)!=report['inherited_anchors'] or anchor_error>1e-10:
        raise ValueError('Inherited anchors differ from the frozen reference')
    if max_rotation_error>1e-6 or max_center_error>1e-6:
        raise ValueError('Rotation or camera-center convention check failed')
    t=np.array(translation);r=np.array(rotation)
    support=[row for row in poses['frames'] if row.get('quality') is not None]
    weak=[row['image_path'] for row in support if row['quality']['inliers']<50]
    # NaNs represent failed endpoints; plots do not invent a pose at those times.
    quality=dict(reference_map_unchanged=True,anchor_count_preserved=len(anchors),
        anchor_max_matrix_difference=anchor_error,max_rotation_orthonormality_error=max_rotation_error,
        max_camera_center_consistency_error=max_center_error,holdout_present=False,
        translation_step_arbitrary_units=dict(median=float(np.nanmedian(t)),p95=float(np.nanquantile(t,.95)),max=float(np.nanmax(t))),
        rotation_step_degrees=dict(median=float(np.nanmedian(r)),p95=float(np.nanquantile(r,.95)),max=float(np.nanmax(r))),
        motion_review_thresholds=dict(translation_step_arbitrary_units=.5,rotation_step_degrees=10),
        motion_review_candidates=jumps,fullrate_pose_sha256=hashlib.sha256(pose_file.read_bytes()).hexdigest(),
        minimum_pnp_inliers=min(row['quality']['inliers'] for row in support),
        lower_support_frames_below_50=len(weak),lower_support_images=weak,
        caution='No interpolation; heuristic jump checks and fitted residuals are not ground-truth validation.')
    (work/'quality-checks.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
    for lang in ['en','es']:
        fig=plt.figure(figsize=(14,8),layout='constrained')
        axes=fig.subplots(2,2,gridspec_kw=dict(height_ratios=[1.4,1]))
        axes[0,1].set_axis_off()
        heat=axes[0,0]
        heat.imshow(np.array(grid),aspect='auto',interpolation='nearest',cmap=ListedColormap(['#b54735','#267ca6','#039487']),vmin=0,vmax=2)
        heat.set_yticks(range(len(by_passage)),sorted(by_passage),fontsize=7)
        heat.set_xlabel('Clip frame index (zero-based)' if lang=='en' else 'Índice de imagen (desde cero)')
        heat.set_title('Pose coverage: blue = PnP, teal = anchor, red = failure' if lang=='en' else 'Poses: azul = PnP, verde = referencia, rojo = fallo',fontsize=10)
        text=(f"{report['localized_frames']} / {report['total_frames']} poses\n\n{report['new_localized_frames']} image-based localizations\n{report['inherited_anchors']} original anchors\n{report['failed_frames']} failures\n\ncam07 excluded\nFixed intrinsics and sparse map\nNo interpolated replacement" if lang=='en' else
              f"{report['localized_frames']} / {report['total_frames']} poses\n\n{report['new_localized_frames']} localizaciones por imagen\n{report['inherited_anchors']} referencias originales\n{report['failed_frames']} fallos\n\ncam07 excluida\nMapa e intrínsecos fijos\nSin sustitución interpolada")
        axes[0,1].text(.05,.9,text,va='top',fontsize=14,color='#18343f')
        for array,ax,label in [(t,axes[1,0],'Translation per frame (arbitrary units)' if lang=='en' else 'Traslación por imagen (unidades arbitrarias)'),(r,axes[1,1],'Rotation per frame (degrees)' if lang=='en' else 'Rotación por imagen (grados)')]:
            time=np.arange(1,109)/30
            ax.fill_between(time,np.nanquantile(array,.05,axis=0),np.nanquantile(array,.95,axis=0),alpha=.25,color='#267ca6',label='5–95%')
            ax.plot(time,np.nanmedian(array,axis=0),color='#007c78',label='Median' if lang=='en' else 'Mediana')
            ax.set(xlabel='Clip time (s)' if lang=='en' else 'Tiempo del clip (s)',ylabel=label)
            ax.grid(alpha=.2);ax.legend(fontsize=9)
        fig.suptitle('Full-rate camera localization against a frozen background map' if lang=='en' else 'Localización de cámaras a frecuencia completa con mapa fijo',fontsize=15)
        fig.savefig(work/f'fullrate-quality.{lang}.png',dpi=140);plt.close(fig)
    print(json.dumps(quality,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace',type=Path,nargs='?',default=ROOT/'outputs/replay-fullrate-poses')
    audit(parser.parse_args().workspace)
