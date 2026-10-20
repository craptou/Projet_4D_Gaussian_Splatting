"""Bounded execution check, not a quality experiment."""
OptimizationParams = dict(iterations=10, coarse_iterations=2, batch_size=1, dataloader=False,
                          densify_until_iter=0, pruning_from_iter=1000)
ModelHiddenParams = dict(net_width=64, multires=[1, 2], defor_depth=0,
    kplanes_config=dict(grid_dimensions=2, input_coordinate_dim=4, output_coordinate_dim=16,
                        resolution=[32, 32, 32, 25]))
