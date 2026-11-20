# Milestones and risk register

**20 November update:** prioritize the [DyNeRF reference gate](dynerf.en.md) on Colab. Data/calibration inspection, training-only sparse initialization and a single-frame held-out PnP check passed on CPU. GPU installation, optimization and rendering remain pending. With the owner's stated 5–10 hours, first explain the split/projection/geometry evidence, then run the bounded notebook; do not promise a completed True Skate reconstruction at the next review. After the reference gate, test fixed capture; retain moving-camera estimation as a separate extension.

[Español](roadmap.es.md) · Baseline: 18 November 2026 · No course deadline supplied.

**Final project: Computer Vision.** The [course map](course-alignment.en.md) links each technical stage to supplied notes. The table below is the project's proposed validation plan, not the professor's official rubric.

| ID | Milestone | Status | Acceptance evidence |
|---|---|---|---|
| M1 | Audited, versioned project and pinned upstream | Done locally | Git history, audit, recursive submodules |
| M2 | Automated replay preparation | Demonstrated | 26 candidate cuts, timing diagnostic, tests |
| M3 | Sampled moving-camera calibration | Demonstrated on sample | 175/175 images in one model; explicit crop and masks |
| M4 | Full-rate poses and camera validation | Coverage demonstrated; validation partial | 2725/2725 accepted, frozen anchors, no flagged jumps; lower-support review and intrinsics sensitivity still needed |
| M5 | Official 4DGS reproduction | Blocked by environment | CUDA modules import; official scene loads; 2 coarse + 10 fine iterations; test renderer produces images |
| M6 | Per-frame dataset loading | Pending; depends on M4/M5 | Synthetic known poses/time; fixed-camera regression; disjoint view IDs |
| M7 | Dynamic reconstruction and held-out evaluation | Pending; depends on M5/M6 | Frozen model; cam07 localized; matched-time render; documented PSNR/SSIM/LPIPS |

M4 and environment provisioning may proceed independently. M5 must pass before custom dynamic training; sampled SfM preparation does not satisfy the reproduction gate.

For the final review, also prepare a world/camera/image projection example (Viewing, PDF pp. 12–15), explain pixel/time sampling choices (pp. 5–6, 18–27), and distinguish sampled trajectory checks (pp. 40–44) from interpolated or measured full-rate poses. Present future Gaussian rasterization against the course pipeline (pp. 15–18). These are proposed learning demonstrations; the final-project brief may add or change requirements.

| Risk | Present evidence | Response / check |
|---|---|---|
| Replay state drift | Score onset differs by ≤1 frame | Inspect more fast-motion events; retain offsets and source indices |
| Moving camera treated as fixed | Proven upstream loader assumption | Keep fixed pipeline blocked; validate per-image loader |
| Intrinsics or geometry bias | Shared focal/principal-point assumption; arbitrary scale | Test model sensitivity, projection checks and trajectory continuity |
| Dynamic foreground contamination | Conservative rectangular feature masks | Review coverage; keep board visible in future training images |
| Sparse success mistaken for final quality | Low reprojection error only | Report novel-view metrics only after true held-out rendering |
| Limited compute | RTX 4050 Laptop, 6 GB; training stack missing | Bounded official smoke run before longer jobs |
| Professor access and publication | Published public repository on 19 November; `main` pushed | Share the repository URL; keep review links and commits current |

No milestone dates, workload estimates or grade weights are asserted without course constraints. Review after each experiment, not only before the presentation.
