"""Restricted single-instant control, 200 coarse + 2000 fine steps; renderer stays undeformed."""
_base_='./true-skate-fixed-pilot.py'
ModelHiddenParams=dict(time_smoothness_weight=0.,plane_tv_weight=0.,l1_time_planes=0.)
