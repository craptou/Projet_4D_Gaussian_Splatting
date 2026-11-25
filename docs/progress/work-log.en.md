# Work log and evidence

[Español](work-log.es.md) · Checkpoint: 18 November 2026

**24 November 2026 — first joint temporal model:** assembled 42 training /3 validation images at normalized times0,5/9,1 from safe static datasets, with canonical first-instant seeds and37 available training masks. Ran a3k pilot and separate6k duration control; evaluated same-run3k/6k checkpoints at3 supervised and7 intermediate timestamps against frozen time. Longer fitting improves observed targets, but middle-board shape, interpolation and background stability remain poor. [Recorded comparisons, metrics, limitations and next tests](joint-temporal.en.md). No faithful flip or physical tracking claim.

**24 November 2026 — three-instant static check:** completed two new safe-scale 200+2,000-step static fits at nominal −0.85 s and −0.40 s around the existing −0.60 s fit. Board recognizable in repeated validation view20 at all three instants. Keep 14 RGB training cameras; tiny early masks13/14 are omitted from carving/loss and their region metrics are unavailable, not NaN. [Results, snapshot display, commands and next temporal gate](multi-instant.en.md). Three independent models, no learned temporal interpolation or tracking.

**24 November 2026 — confirmed near-clip integration bug:** camera/mask audit finds the view20 camera background-consistent and its old mask incomplete. CUDA clips seeds at depth0.2 despite Python Camera near0.01; 99.93% of initial board seeds were clipped in view20. Uniform scale4 preserves projections and restores visibility. Safe-scale retraining makes the board recognizable in validation view20 (approximate deck PSNR15.75→22.91 dB). Added a blocking seed-visibility gate and corrected earlier interpretations. [Evidence, controls and reproduction](near-clip-fix.en.md). No dynamic/rotation result claimed.

**24 November 2026 — single-instant static controls:** full 17-view silhouette/box consistency fails under current cameras and nominal time. Timing offsets fail to resolve three views; independent-focal calibration is rejected as degenerate. A restricted 14-view, one-instant fit with 13 silhouette-volume masks produces a recognizable board in inspected training views, but fails on reserved view20. Fixed-geometry/degree-zero-color control does not repair it. [Evidence, before/after images and commands](static-board.en.md). No learned motion or tracking is claimed.

**24 November 2026 — foreground control:** reviewed action phases across 18 views and all 13 samples of three nearby views; exact synchronization remains uncertain. Completed an RTX 4050 control with unchanged baseline inputs and 200 coarse + 5,000 fine steps, adding a view19-only foreground loss. Masked training fit improves, but broad dark spillover appears and reserved-view full-image PSNR declines. [Results, commands, comparisons and next hypothesis](foreground-trial.en.md). The earlier chronology below retains its original checkpoint context.

Entries below are reconstructed from Git history and retained run artifacts. They record actual checkpoints, not continuous weekly activity. Commit hashes can be inspected with `git show <hash>` after cloning.

| Date | Problem / action | Evidence and outcome | Interpretation / next step |
|---|---|---|---|
| 2026-10-19 | Audit machine, pin official upstream, initialize project | `b24c12f`, `34d109d`; [initial system report](../system-report.md) | GPU identified; CUDA build environment unavailable |
| 2026-10-19 | Build extraction/validation helpers and controlled fixed-camera wrappers | `a8206c9`; initial 10 tests passed | CPU preparation works; wrappers not proven end-to-end |
| 2026-10-19 | Inspect fixed-camera assumptions and plan moving-pose research | `774e1b5`; [source analysis](../moving-camera-plan.md) | Reject silent use of one pose for a moving sequence |
| 2026-10-19 | Correct audit output encoding and missing hardware fields | `d036ce6` | Audit made readable; not a GPU-training success |
| 2026-11-18 | Owner supplies original recording and eight manual cuts; automate segmentation | `a23b464`; [capture review](../capture-review-2026-11-18.md) | 26 candidate passages, 109 frames each; 16 helper tests |
| 2026-11-18 | Crop and mask sampled views; run initial sparse pilot | `c73a1f9`; [pose report](../pose-pilot-2026-11-18.md) | 33/42 images registered; limited overlap/coverage investigated |
| 2026-11-18 | Add intermediate viewpoints and rerun without relaxed mapper thresholds | `c73a1f9`, `64a3fc1`; [checkpoint JSON](../evidence/checkpoint-2026-11-18.json) | 175/175 images, 8767 points, 0.473 px; 19 tests |
| 2026-11-18 | Check score onset and reserve cam07 | `c73a1f9`; same run documentation | Event spread one frame; no held-out scene evaluation yet |
| 2026-11-18 | Prepare bilingual review documents, evidence and presentations | Current documentation commits; inspect `git log -- presentations docs/progress` | Publish reviewable checkpoint; continue dated updates |
| 2026-11-18 | Owner clarifies final-project role and supplies course notes | [Course map](course-alignment.en.md), [PDF fingerprint](../evidence/course-context.json) | Reframe as Computer Vision final project; link topics by page without inventing a rubric |
| 2026-11-18 | Localize the remaining 2550 training images; investigate 31 initial failures | `50b2fc3`; [full-rate experiment](fullrate.en.md), [evidence](../evidence/fullrate-2026-11-18.json) | 2725/2725 accepted with original anchors/map unchanged; 132 lower-support cases retained for review; 25 tests |
| 2026-11-19 | Owner supplies remote; inspect and publish existing history | [GitHub repository](https://github.com/craptou/Projet_4D_Gaussian_Splatting); `git push -u origin main` | Empty remote, successful normal push; public visibility and default `main` verified |

## Decisions supported by this history

- Preserve the upstream submodule; changes live in wrappers and scripts.
- Prefer automated cursor-based cutting over unequal manual cuts.
- Use per-image background SfM because the camera actually moves.
- Add viewpoint overlap before loosening reconstruction thresholds.
- Keep cam07 outside geometry optimization; inspect its timing separately.
- Report sparse registration success separately from unexecuted 4DGS training.

## Failures and unresolved blockers

The first sparse run missed nine images. Intermediate views resolved that registration issue; the later full-rate experiment is documented separately. Audio alignment was inconclusive. A CUDA training environment and official sample reproduction remain absent. Publication was pending on 18 November but succeeded on 19 November through Git, despite the optional GitHub CLI remaining unauthenticated. No failed command is counted as a completed milestone.

### 20 November 2026 — real-data reference preparation

Selected DyNeRF `cut_roasted_beef` and Colab for the next execution gate. Downloaded/inspected 20 synchronized-by-author camera videos; reserved cam00. Fixed-calibration CPU triangulation produced 3,390 points (0.710 px mean reprojection error). SIFT/PnP localized held-out frame 0 with 961 inliers and 0.01094° difference from supplied calibration. Added an unexecuted bounded Colab notebook, a compact licensed initialization artifact and bilingual protocol. These results check geometry preparation, not dynamic training or reconstruction quality. [Commands, measured evidence, limitations and learning objectives](dynerf.en.md).

## How to continue the log

Use the [checkpoint template](../templates/checkpoint.en.md). Record one dated entry per meaningful result, with exact commands or commit, before/after evidence, limitations and the next acceptance test. Never backfill unperformed work or revise old measurements without recording why.
