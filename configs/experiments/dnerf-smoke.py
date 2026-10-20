"""Keep D-NeRF defaults except bounded iteration count and disabled densification."""
_base_ = '../../third_party/4DGaussians/arguments/dnerf/bouncingballs.py'
OptimizationParams = dict(iterations=10, coarse_iterations=2, batch_size=1,
                          dataloader=False, densify_until_iter=0)
