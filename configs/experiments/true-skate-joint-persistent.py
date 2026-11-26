"""Appearance control: same actor-only dataset/budget, no temporal opacity or SH changes."""
_base_='./true-skate-joint-three-duration.py'
ModelHiddenParams=dict(no_do=True,no_dshs=True)
