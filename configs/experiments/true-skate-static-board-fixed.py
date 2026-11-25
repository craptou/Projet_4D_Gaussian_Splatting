"""Appearance-only static control: fixed positions/scales/rotations, no densification, degree-zero color."""
_base_='./true-skate-static-board.py'
ModelParams=dict(sh_degree=0)
OptimizationParams=dict(position_lr_init=0.,position_lr_final=0.,scaling_lr=0.,rotation_lr=0.,densify_until_iter=0)
