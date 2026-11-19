# Work log and evidence

[Español](work-log.es.md) · Checkpoint: 18 November 2026

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

## How to continue the log

Use the [checkpoint template](../templates/checkpoint.en.md). Record one dated entry per meaningful result, with exact commands or commit, before/after evidence, limitations and the next acceptance test. Never backfill unperformed work or revise old measurements without recording why.
