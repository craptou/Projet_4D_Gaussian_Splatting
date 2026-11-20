"""Execution gate only: official DyNeRF model, sparse initialization, 12 steps."""
_base_ = '../../third_party/4DGaussians/arguments/dynerf/cut_roasted_beef.py'
OptimizationParams = dict(iterations=10, coarse_iterations=2, batch_size=1,
                          dataloader=True, densify_until_iter=0)
