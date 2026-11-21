"""Bounded quality pilot: 200 coarse + 3000 fine, four densification events."""
_base_ = '../../third_party/4DGaussians/arguments/dynerf/cut_roasted_beef.py'
OptimizationParams = dict(
    iterations=3000, coarse_iterations=200, batch_size=1, dataloader=True,
    densify_from_iter=200, densify_until_iter=1300, densification_interval=300,
    add_point=False,
)
