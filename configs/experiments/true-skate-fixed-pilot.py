"""First bounded True Skate attempt: 200 coarse + 2000 fine, small grid."""
ModelParams = dict(white_background=False, eval=True, add_points=False)
OptimizationParams = dict(iterations=2000, coarse_iterations=200, batch_size=1,
    dataloader=False, densify_from_iter=200, densify_until_iter=1300,
    densification_interval=300, opacity_reset_interval=60000, add_point=False)
ModelHiddenParams = dict(net_width=64, multires=[1,2], defor_depth=0,
    kplanes_config=dict(grid_dimensions=2, input_coordinate_dim=4,
        output_coordinate_dim=16, resolution=[32,32,32,13]),
    no_do=False, no_dshs=False, no_ds=False,
    plane_tv_weight=.0002, time_smoothness_weight=.001, l1_time_planes=.0001)
