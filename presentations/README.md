# Progress presentation / Presentación de avance

## Latest English talk — 26 November 2026

**About ten minutes: twelve slides, with function references integrated into the relevant concepts.** Part1 explains image preparation, cameras, projection, Gaussian representation, rendering, training and time. Part2 covers acquisition, the kitchen reference, weaker True Skate results and the mask experiments already completed. No code appendix. The PowerPoint embeds the three-second kitchen-model video and English speaker notes.

[French learning guide: cameras, Gaussian methods, course concepts and exercises](understand-the-project.fr.md). A read-only projection exercise runs with `python scripts/learn_camera_projection.py`; add `--real` to inspect the existing local camera dataset.

[PowerPoint](progress-2026-11-26.en.pptx) · [Slide PDF](progress-2026-11-26.en.pdf) · [Clear oral script, PDF](progress-2026-11-26.script.en.pdf) · [English script, function links and sources](progress-2026-11-26.en.md) · [French preparation guide](preparation-2026-11-26.fr.md) · [Editable slide content](progress-2026-11-26.en.json).

Build with `python scripts/build_short_progress.py`; validate and render the review pages with `python scripts/validate_short_progress.py`. The authoring script uses tracked evidence images and the existing reference clip; no GPU checkpoints or raw captures are required. Exported slides embed their figures and the reference video. The historical bilingual deck below remains the 18 November checkpoint.

## Archived bilingual presentation — 18 November 2026

Checkpoint / corte: **2026-11-18** · **12 slides per language / 12 diapositivas por idioma**

**Computer Vision · Final course project / Proyecto final del curso.** Slide 2 maps the supplied course topics to the project, with PDF page references. / La diapositiva 2 vincula los temas del curso con el proyecto e indica páginas del PDF.

| Language / idioma | View / ver | Edit / editar | Outline and notes / guion y notas |
|---|---|---|---|
| English | [PDF](progress.en.pdf) | [PowerPoint](progress.en.pptx) | [Markdown](progress.en.md) |
| Español | [PDF](progress.es.pdf) | [PowerPoint](progress.es.pptx) | [Markdown](progress.es.md) |

Content covers the research question, pipeline, capture evidence, moving-camera limitation, synchronization, sparse SfM results, holdout design, traceable work, limitations and next experiments. It does not present an untrained 4DGS model as a completed result.

El contenido incluye pregunta de investigación, arquitectura, capturas, cámara móvil, sincronización, resultados dispersos de SfM, evaluación reservada, seguimiento, límites y siguientes experimentos. No presenta un modelo 4DGS no entrenado como un resultado terminado.

Edit [deck.json](deck.json), then run `python scripts/build_progress_slides.py` from repository root. Run `python scripts/validate_review_docs.py` after rebuilding. See [maintenance instructions / mantenimiento](../docs/progress/README.md) for dependencies, evidence provenance and publishing. The PowerPoint files contain editable text and speaker notes; the figures are embedded images. PDF rendering was visually inspected; native PowerPoint rendering was not independently tested.
