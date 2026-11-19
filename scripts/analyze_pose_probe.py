"""Export sparse geometry, camera trajectories and a static scientific figure."""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
import pycolmap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import _bootstrap


def analyze(work):
    report=json.loads((work/"report.json").read_text(encoding="utf-8"))
    if not report["models"]:
        raise ValueError("No reconstructed model")
    best=max(report["models"],key=lambda m:m["registered_images"])
    model=pycolmap.Reconstruction(work/"sparse"/str(best["model_id"]))
    records=json.loads((work/f"poses-model-{best['model_id']}.json").read_text(encoding="utf-8"))["images"]
    for r in records:
        r.setdefault("camera_id",r["image_path"].split('/')[0])
        r.setdefault("clip_frame_index",int(Path(r["image_path"]).stem.split('_')[-1])-1)
    xyz=np.array([p.xyz for p in model.points3D.values()])
    colors=np.array([p.color for p in model.points3D.values()])/255
    lo,hi=np.quantile(xyz,[0.01,0.99],axis=0)
    keep=np.all((xyz>=lo)&(xyz<=hi),axis=1)
    tracks=Counter()
    for p in model.points3D.values():
        names={model.image(e.image_id).name.split('/')[0] for e in p.track.elements}
        tracks[len(names)]+=1
    trajectories={}
    fig=plt.figure(figsize=(15,7),layout="constrained")
    ax=fig.add_subplot(121,projection='3d')
    ax.scatter(*xyz[keep].T,c=colors[keep],s=2,alpha=.7)
    ax2=fig.add_subplot(122)
    passages=sorted({r["camera_id"] for r in records})
    palette=plt.get_cmap('turbo')
    for i,name in enumerate(passages):
        rows=sorted((r for r in records if r["camera_id"]==name),key=lambda r:r["clip_frame_index"])
        centers=np.array([r["center_world"] for r in rows])
        path=np.linalg.norm(np.diff(centers,axis=0),axis=1).sum()
        trajectories[name]=dict(registered_frames=len(rows),sampled_indices=[r["clip_frame_index"] for r in rows],
            path_length_arbitrary_units=float(path),endpoint_distance_arbitrary_units=float(np.linalg.norm(centers[-1]-centers[0])))
        color=palette(i/max(1,len(passages)-1))
        ax.plot(*centers.T,color=color,linewidth=1.3)
        ax.scatter(*centers[0],color=color,s=18)
        d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(centers,axis=0),axis=1))]
        ax2.plot([r["clip_frame_index"]/30 for r in rows],d,label=name,color=color,marker='.',markersize=3)
    ax.set(xlabel='World X (arbitrary units)',ylabel='World Y',zlabel='World Z',
           title=f"Sparse background: {len(xyz)} points\nCamera-center paths (1% point-cloud outliers hidden)")
    ax.set_box_aspect((1,1,1))
    ax2.set(xlabel='Clip time (seconds)',ylabel='Cumulative camera-center travel (arbitrary units)',
            title='Recovered motion per passage; gaps are not interpolated poses')
    ax2.legend(fontsize=7,ncol=3)
    ax2.grid(alpha=.25)
    fig.suptitle(f"Moving-camera SfM pilot: {best['registered_images']}/{report['image_count']} images; reprojection {best['mean_reprojection_error']:.2f} px\nTraining fit only; held-out cam07 excluded; geometry not metrically calibrated",fontsize=11)
    fig.savefig(work/'geometry-and-trajectories.png',dpi=160)
    fig.savefig(work/'geometry-and-trajectories.svg')
    plt.close(fig)
    result=dict(point_count=len(xyz),cross_passage_points=sum(n for k,n in tracks.items() if k>=2),
        tracks_by_distinct_passage_count=dict(tracks),trajectories=trajectories,
        caution='Sparse reprojection fit does not prove correct scale, dynamics, synchronization, or novel-view quality.')
    (work/'geometry-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('workspace',type=Path)
    analyze(p.parse_args().workspace)
