"""Time-invariant background routing using seed provenance and upstream parent-label propagation."""
_background_count=None
_installed=False


def gate_outputs(base,deformed,dynamic):
    import torch
    if len(base)!=5 or len(deformed)!=5 or dynamic.ndim!=1 or dynamic.dtype!=torch.bool:raise ValueError('Invalid deformation routing inputs')
    outputs=[]
    for original,changed in zip(base,deformed):
        if original.shape!=changed.shape or len(original)!=len(dynamic):raise ValueError('Point labels and tensors differ')
        mask=dynamic.reshape((len(dynamic),)+(1,)*(original.ndim-1))
        outputs.append(torch.where(mask,changed,original))
    return tuple(outputs)


def configure(background_count=None):
    global _background_count,_installed
    if background_count is not None and background_count<=0:raise ValueError('Invalid background seed count')
    _background_count=background_count
    if _installed:return
    from scene.gaussian_model import GaussianModel
    original_init=GaussianModel.__init__
    original_create=GaussianModel.create_from_pcd
    original_load=GaussianModel.load_model
    original_update=GaussianModel.update_deformation_table

    def initialize(self,*args,**kwargs):
        original_init(self,*args,**kwargs)
        self._actor_background_count=_background_count
        if self._actor_background_count is None:return
        forward=self._deformation.forward
        def routed(point,scales=None,rotations=None,opacity=None,shs=None,times_sel=None):
            outputs=forward(point,scales,rotations,opacity,shs,times_sel)
            return gate_outputs((point,scales,rotations,opacity,shs),outputs,self._deformation_table)
        self._deformation.forward=routed

    def create(self,*args,**kwargs):
        original_create(self,*args,**kwargs)
        count=self._actor_background_count
        if count is None:return
        import torch
        if count>=len(self.get_xyz):raise ValueError('No actor seeds')
        self._deformation_table=torch.arange(len(self.get_xyz),device=self.get_xyz.device)>=count

    def load(self,path):
        if self._actor_background_count is not None:
            from pathlib import Path
            if not (Path(path)/'deformation_table.pth').exists():raise ValueError('Actor provenance labels missing from checkpoint')
        original_load(self,path)
        if self._actor_background_count is not None:
            table=self._deformation_table
            if len(table)!=len(self.get_xyz) or not table.any() or table.all():raise ValueError('Invalid saved actor/background partition')

    def update(self,*args,**kwargs):
        if self._actor_background_count is not None:raise ValueError('Seed provenance must not be replaced by motion-threshold labels')
        return original_update(self,*args,**kwargs)

    GaussianModel.__init__=initialize
    GaussianModel.create_from_pcd=create
    GaussianModel.load_model=load
    GaussianModel.update_deformation_table=update
    _installed=True


def configure_from_source(source):
    import json
    manifest=json.loads((source/'manifest.json').read_text())
    count=None
    if manifest.get('actor_only_deformation'):
        count=json.loads((source/'preparation.json').read_text())['background_points']
    configure(count)


def audit_partition(model):
    """Check every background output at three times on the actual loaded model."""
    import torch
    if getattr(model,'_actor_background_count',None) is None:return None
    dynamic=model._deformation_table
    base=(model.get_xyz,model._scaling,model._rotation,model._opacity,model.get_features)
    errors=[0.]*5
    with torch.no_grad():
        for time in (0.,5/9,1.):
            times=torch.full((len(dynamic),1),time,device=model.get_xyz.device)
            outputs=model._deformation(*base,times)
            for i,(original,changed) in enumerate(zip(base,outputs)):
                errors[i]=max(errors[i],float((changed[~dynamic]-original[~dynamic]).abs().max()))
    if any(errors):raise ValueError('Background attributes depend on time')
    return dict(background_descendants=int((~dynamic).sum()),actor_descendants=int(dynamic.sum()),
        times=[0.,5/9,1.],max_background_absolute_delta=dict(zip(['xyz','scale','rotation','opacity','sh'],errors)),
        note='Seed ancestry, not semantic segmentation; actor occlusion can still change background pixels.')
