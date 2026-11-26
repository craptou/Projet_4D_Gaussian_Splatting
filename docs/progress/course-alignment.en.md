# Course alignment — final project

**26 November2026 update:** the [short English presentation](../../presentations/progress-2026-11-26.en.pdf) uses four direct links to the supplied notes: world/camera transformations (pp.3–4,13–15), perspective and visibility/clipping (pp.12–18), frame sampling and temporal alignment (pp.21–22), and rasterization (pp.15–18). The static near-clip correction is a concrete viewing/visibility example; saved GPU renders demonstrate the forward stage. The latest pilot has11 training cameras, ten supervised times,563×1218 images and reserved view20. COLMAP and Gaussian methods are reused implementations, not claimed course algorithms implemented from scratch. No FFT, SLERP or physical light-transport implementation is claimed. The detailed mapping below preserves the18November preparation-stage context and its older dataset values.

**Course designation supplied by the owner:** Computer Vision. This repository documents its **final course project**, not an independent graphics exercise. [Español](course-alignment.es.md)

## Source and scope

Reference supplied locally: **course topic notes**, credited to **Pablo Figueroa** on PDF page 1, 46 pages. Page references below are **one-based PDF page numbers**, including the title page. The [source fingerprint and topic index](../evidence/course-context.json) identify the exact reviewed copy without publishing its filename. The original PDF remains local; the repository tracks this page-referenced interpretation rather than redistributing the complete teaching document.

The supplied material describes itself as weekly topic summaries and contains substantial graphics, imaging and mathematical content. The owner's course name is retained as Computer Vision; the notes' graphics topics are linked explicitly rather than treating computer vision and graphics as identical. No final-project assignment, marking weights, delivery date or mandatory presentation format was found in this copy. The owner separately stated that project follow-up is graded; that requirement is a user-provided constraint, not a quotation from the PDF.

## How this final project uses the course

| Topic in the supplied notes | PDF pages | Project application | Current evidence / remaining demonstration |
|---|---|---|---|
| Linear algebra, homogeneous coordinates, projective geometry | 3–4 | Represent world-to-camera transformations and project reconstructed points into images | Estimated per-image `[R|T]`; rotation checks; explicit coordinate conventions |
| Viewing: viewport, camera, perspective projection | 12–15 | Distinguish intrinsics/extrinsics and account for crop-induced pixel-coordinate changes | Shared camera model; crop principal point `(296,540)`; known-pose/sensitivity validation still needed |
| Raster images and color | 5–6 | Treat recordings as sampled pixel arrays; preserve dimensions and document color/encoding | 720 × 1280 recording, common 592 × 820 crop; future metrics must fix color-space conventions |
| Signal processing, sampling, filtering and reconstruction | 18–27 | Keep common source frame indexes; reason about temporal aliasing, interpolation and resampling | No independent view resampling; score event differs by ≤1 frame; full-state synchronization not established |
| Graphics pipeline, rasterization, visibility and antialiasing | 15–18 | Explain future projection/compositing of Gaussian primitives into a novel image | Future 4DGS stage; current point cloud is not a rasterized dynamic model |
| Data structures for graphics | 32–35 | Compare scene representations and discuss memory/visibility costs | Sparse points and camera graph exist; learned Gaussians and performance comparisons remain future work |
| Curves, derivatives and continuity | 40–44 | Analyze camera-center paths and time-dependent motion | Now 109 estimated poses per training passage; adjacent-frame checks, no interpolated substitutes; ground truth still unavailable |
| Surface shading, texture mapping and physical light transport | 9–11, 27–32, 35–40 | Discuss view-dependent appearance and distinguish learned image synthesis from explicit light transport | Contextual comparison only; no custom BRDF, texture-mapping, ray-tracing or path-tracing implementation is claimed |

SfM, SIFT, bundle adjustment and 4DGS are project techniques that build on these concepts. The PDF does not name all of them as required course algorithms. Reusing PyCOLMAP and the official 4DGS implementation is disclosed; the project's own work is in data preparation, camera-model safeguards, experimental design and evaluation tooling.

## The vision question and the graphics step

The **inverse** part estimates cameras and a scene representation from observed images. The **forward** part uses that representation to synthesize pixels from a new camera at a chosen replay time. A successful final project must make both directions understandable and validate their connection.

For a world point `X`, the image model is `p ~ K[R|T]X`. Cropping changes the image-coordinate origin and therefore the principal point. A moving replay camera requires `[R(c,t)|T(c,t)]`; sharing a single pose across time would contradict the capture. The proposed novel-view stage uses time-conditioned Gaussian parameters and camera projection. It should not be described as implementing the course's entire traditional triangle pipeline or a physical path tracer.

## Course-linked demonstrations to prepare

These are **proposed project demonstrations**, not an extracted grading rubric:

1. Explain a world/camera/image coordinate example and show the effect of the crop on `K`.
2. Compare a fixed-pose hypothesis with the recovered moving trajectories; show why the upstream loader is unsuitable unchanged.
3. Display the same replay event across viewpoints and discuss what one-frame agreement does and does not prove.
4. Show sparse-background evidence separately from a future dynamic reconstruction; explain representation and visibility choices.
5. Once training works, vary camera and replay time independently, then compare held-out cam07 images with the corresponding renders.
6. Provide commands, configuration, observed failures and a dated work log so that progress can be assessed independently of visual polish.

## Assessment information still needed

The exact final-project brief, grading weights, presentation duration, deadline, group/authorship rules and any implementation-from-scratch requirement are not established by this PDF. They should be added when supplied; the current roadmap must not be represented as the professor's official rubric. Current measured results remain unchanged by this documentation update.
