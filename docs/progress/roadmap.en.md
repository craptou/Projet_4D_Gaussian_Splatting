# Milestones and risk register

[Español](roadmap.es.md) · Baseline: 18 November 2026 · No course deadline supplied.

| ID | Milestone | Status | Acceptance evidence |
|---|---|---|---|
| M1 | Audited, versioned project and pinned upstream | Done locally | Git history, audit, recursive submodules |
| M2 | Automated replay preparation | Demonstrated | 26 candidate cuts, timing diagnostic, tests |
| M3 | Sampled moving-camera calibration | Demonstrated on sample | 175/175 images in one model; explicit crop and masks |
| M4 | Full-rate poses and camera validation | Pending | All required training images registered, fast-motion checks, intrinsics sensitivity and known-pose projection checks |
| M5 | Official 4DGS reproduction | Blocked by environment | CUDA modules import; official scene loads; 2 coarse + 10 fine iterations; test renderer produces images |
| M6 | Per-frame dataset loading | Pending; depends on M4/M5 | Synthetic known poses/time; fixed-camera regression; disjoint view IDs |
| M7 | Dynamic reconstruction and held-out evaluation | Pending; depends on M5/M6 | Frozen model; cam07 localized; matched-time render; documented PSNR/SSIM/LPIPS |

M4 and environment provisioning may proceed independently. M5 must pass before custom dynamic training; sampled SfM preparation does not satisfy the reproduction gate.

| Risk | Present evidence | Response / check |
|---|---|---|
| Replay state drift | Score onset differs by ≤1 frame | Inspect more fast-motion events; retain offsets and source indices |
| Moving camera treated as fixed | Proven upstream loader assumption | Keep fixed pipeline blocked; validate per-image loader |
| Intrinsics or geometry bias | Shared focal/principal-point assumption; arbitrary scale | Test model sensitivity, projection checks and trajectory continuity |
| Dynamic foreground contamination | Conservative rectangular feature masks | Review coverage; keep board visible in future training images |
| Sparse success mistaken for final quality | Low reprojection error only | Report novel-view metrics only after true held-out rendering |
| Limited compute | RTX 4050 Laptop, 6 GB; training stack missing | Bounded official smoke run before longer jobs |
| Professor cannot access repository | No authenticated GitHub session | Create/push private repository, then grant the professor access separately |

No milestone dates, workload estimates or grade weights are asserted without course constraints. Review after each experiment, not only before the presentation.
