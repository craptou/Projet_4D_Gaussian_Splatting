"""Translate the scientific figure by plotting the same native SfM data again."""
import json
from pathlib import Path
import numpy as np
import pycolmap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
work=ROOT/'outputs/replay-pose-expanded'
report=json.loads((work/'report.json').read_text())
model=pycolmap.Reconstruction(work/'sparse/0')
records=json.loads((work/'poses-model-0.json').read_text())['images']
xyz=np.array([p.xyz for p in model.points3D.values()])
colors=np.array([p.color for p in model.points3D.values()])/255
lo,hi=np.quantile(xyz,[.01,.99],axis=0)
keep=np.all((xyz>=lo)&(xyz<=hi),axis=1)
fig=plt.figure(figsize=(15,7),layout='constrained')
ax=fig.add_subplot(121,projection='3d');ax2=fig.add_subplot(122)
ax.scatter(*xyz[keep].T,c=colors[keep],s=2,alpha=.7)
passages=sorted({r['camera_id'] for r in records})
palette=plt.get_cmap('turbo')
for i,name in enumerate(passages):
    rows=sorted((r for r in records if r['camera_id']==name),key=lambda r:r['clip_frame_index'])
    centers=np.array([r['center_world'] for r in rows]);color=palette(i/max(1,len(passages)-1))
    ax.plot(*centers.T,color=color,linewidth=1.3);ax.scatter(*centers[0],color=color,s=18)
    distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(centers,axis=0),axis=1))]
    ax2.plot([r['clip_frame_index']/30 for r in rows],distance,label=name,color=color,marker='.',markersize=3)
ax.set(xlabel='X global (unidades arbitrarias)',ylabel='Y global',zlabel='Z global',
    title=f'Fondo disperso: {len(xyz)} puntos\nTrayectorias de cámara; extremos del 1% ocultos por eje')
ax.set_box_aspect((1,1,1))
ax2.set(xlabel='Tiempo del clip (segundos)',ylabel='Recorrido del centro de cámara (unidades arbitrarias)',
    title='Movimiento por pasaje; no se generan poses intermedias')
ax2.legend(fontsize=7,ncol=3);ax2.grid(alpha=.25)
metric=report['models'][0]
fig.suptitle(f"Prueba SfM móvil: {metric['registered_images']}/{report['image_count']} imágenes; reproyección 0,47 px\nAjuste de entrenamiento; cam07 excluida; geometría sin escala métrica",fontsize=11)
target=ROOT/'docs/assets/geometry-and-trajectories.es.png'
fig.savefig(target,dpi=110);plt.close(fig)
print(target)
