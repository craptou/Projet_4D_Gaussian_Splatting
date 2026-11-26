"""Render seed ancestry as foreground contribution, not semantic ground truth."""
def render_labels(camera,model,pipeline):
    import math
    import torch
    from diff_gaussian_rasterization import GaussianRasterizationSettings,GaussianRasterizer
    settings=GaussianRasterizationSettings(image_height=int(camera.image_height),image_width=int(camera.image_width),
        tanfovx=math.tan(camera.FoVx*.5),tanfovy=math.tan(camera.FoVy*.5),bg=torch.zeros(3,device='cuda'),
        scale_modifier=1.,viewmatrix=camera.world_view_transform.cuda(),projmatrix=camera.full_proj_transform.cuda(),
        sh_degree=0,campos=camera.camera_center.cuda(),prefiltered=False,debug=pipeline.debug)
    times=torch.full((len(model.get_xyz),1),camera.time,device='cuda')
    xyz,scales,rotation,opacity,_=model._deformation(model.get_xyz,model._scaling,model._rotation,model._opacity,model.get_features,times)
    labels=model._deformation_table.to(dtype=xyz.dtype)[:,None].repeat(1,3)
    image,_,_=GaussianRasterizer(raster_settings=settings)(means3D=xyz,means2D=torch.zeros_like(xyz),shs=None,
        colors_precomp=labels,opacities=model.opacity_activation(opacity),scales=model.scaling_activation(scales),
        rotations=model.rotation_activation(rotation),cov3D_precomp=None)
    return image[0].clamp(0,1)
