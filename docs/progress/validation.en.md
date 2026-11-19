# Review-package validation

[Español](validation.es.md) · Verified 18 November 2026

Latest full-rate follow-up: **25 helper tests pass**, including known-pose PnP recovery with outliers. The full-rate export was audited for all 2725 frames, exact preservation of 175 anchors, unchanged map/camera fingerprints, rotation/center conventions and adjacent-frame changes. No image is filled by interpolation; 132 lower-support poses remain explicitly marked for review. The earlier 19-test list below records the preceding review package.

- The existing helper suite passed: **19 tests**, including generated-video extraction and held-out exclusion.
- Both presentations were generated from the same bilingual source: **12 English and 12 Spanish slides**, each with speaker notes, PDF and editable PPTX.
- Every PDF page was decoded/rendered. Overview contact sheets and selected full-size slides were inspected for clipping and readable content.
- PPTX slide count, shape bounds, expected evidence text and source-aligned notes were checked. Native PowerPoint rendering was not independently tested.
- All relative links in the review package were checked after generation. The maintenance script repeats this check; it also checks the checkpoint split and registration count.
- Slide figures come from observed game captures and the retained sparse model. The Spanish scientific figure redraws the same points and trajectories with translated labels.
- Evidence records 175/175 sampled image registrations, 8767 points, 8377 cross-passage points and a one-frame score-event spread. No 4DGS training or held-out score is implied.
- Documentation dependencies pass `pip check`; Python scripts compile; Git whitespace checks pass.
- After the owner supplied the course notes, both decks were rebuilt as the final project for Computer Vision. A page-referenced bilingual course map was added. The original PDF fingerprint and 46-page count are checked when that local file is available; it is not required to clone or view the review package.
- Videos, models, databases and full-resolution extracted datasets remain excluded from normal Git. The review package includes only small figures, structured evidence, text and presentation exports.

Recheck with `python scripts/validate_review_docs.py` after changing links or rebuilding slides. Re-run helper tests only when implementation changes require it. Repository publication is separate: GitHub authentication was unavailable during preparation.
