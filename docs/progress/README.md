# Maintaining the project record / Mantener el seguimiento

## English

Start with the [course map](course-alignment.en.md), [report](report.en.md), [work log](work-log.en.md), [roadmap](roadmap.en.md) and [presentation](../../presentations/progress.en.pdf). This is the final project for Computer Vision — CVI 26-2; technical detail remains in the linked experiment documents.

Latest experimental checkpoint: [full-rate poses](fullrate.en.md), with [structured evidence](../evidence/fullrate-2026-11-18.json). The earlier 175-image snapshot remains archived as the sampled-map baseline.

For each meaningful experiment, add a dated [checkpoint](../templates/checkpoint.en.md) with the question, actual work, exact commands/commit, measured result, failure, limitation and next acceptance test. Preserve old measurements. Update both languages together; do not turn planned work into completed work. The initial history contains recorded sessions on 19 October and 18 November 2026, not a fabricated weekly diary. Course notes have now been supplied and mapped by PDF page; an explicit final-project rubric, author display name and deadline remain unprovided.

The tracked [evidence snapshot](../evidence/checkpoint-2026-11-18.json) is a compact extraction of local run reports. It includes the recording SHA-256 and implementation commit, with no personal filesystem paths. Figures are small review exports. Full datasets, trained models and databases remain ignored. The supplied gameplay figures have their own game provenance; the project code license does not assert ownership of game assets.

### Rebuild the presentation

```powershell
.\.venv\Scripts\python.exe -m pip install -r environment/requirements-documentation.txt
.\.venv\Scripts\python.exe scripts/build_progress_slides.py
.\.venv\Scripts\python.exe scripts/validate_review_docs.py
```

Run from repository root. [deck.json](../../presentations/deck.json) is the shared bilingual content source. It creates editable 16:9 PPTX files, matching landscape PDFs, and Markdown outlines with speaker notes. Font discovery prefers Arial, then DejaVu Sans, then ReportLab's bundled Vera; different fonts can change wrapping. The PDF and PPTX are built from the same layout instructions; PDFs are rendered and inspected, while PPTX page bounds, text, slide count and notes are checked structurally. Native PowerPoint rendering was not independently tested.

Tracked images are sufficient to rebuild slides after a clone. Rebuilding the Spanish scientific figure additionally needs the local sparse model and the SfM dependencies: `python scripts/build_review_figure_es.py`. It redraws the same points/trajectories with Spanish labels, without changing poses or experiments.

### Publish for the professor

There was no remote or authenticated GitHub session at this checkpoint. From repository root:

```powershell
.\.tools\gh\bin\gh.exe auth login
.\.tools\gh\bin\gh.exe repo create skate-trick-4dgs --private --source . --remote origin --push
```

Use `gh` instead of the project-local path on another machine. The portable CLI itself is ignored. A private repository requires explicitly granting the professor access; no professor account or email was supplied, and no invitation was sent. After publication, open the repository in a browser and verify both README language links and PDF downloads with an authorized account. If an existing remote is supplied later, use that instead of creating a duplicate. No GitHub Pages site is needed for the repository README or PDF previews.

## Español

Empezar por el [mapa del curso](course-alignment.es.md), el [informe](report.es.md), la [bitácora](work-log.es.md), la [hoja de ruta](roadmap.es.md) y las [diapositivas](../../presentations/progress.es.pdf). Es el proyecto final de Computer Vision — CVI 26-2. Los detalles técnicos permanecen en los experimentos enlazados.

Último corte: [poses completas](fullrate.es.md) y [evidencias](../evidence/fullrate-2026-11-18.json). El corte de 175 imágenes se conserva como referencia histórica del mapa muestreado.

Tras cada experimento significativo, añadir un [corte fechado](../templates/checkpoint.es.md) con pregunta, trabajo realizado, comandos/commit, resultados, fallos, límites y siguiente criterio de aceptación. Conservar las mediciones antiguas y actualizar ambos idiomas. No transformar planes en logros ni inventar actividad semanal. Ya se aportaron apuntes y se referenciaron sus páginas; siguen pendientes rúbrica específica del proyecto final, nombre para la portada y fecha de entrega.

`presentations/deck.json` es la fuente común del contenido bilingüe. Los comandos anteriores generan PowerPoint editable, PDF y guion con notas. Se revisó el PDF renderizado y se verificaron estructuralmente límites, textos, número de diapositivas y notas del PPTX; no se comprobó una renderización independiente en PowerPoint. Los tipos de letra disponibles pueden cambiar los saltos de línea.

Las figuras y el resumen JSON se versionan para permitir revisión sin vídeos. Las grabaciones, bases de datos y modelos completos siguen excluidos. El SHA-256 identifica la grabación requerida para repetir el experimento real. El gráfico español se vuelve a dibujar con los mismos puntos y trayectorias, sin cambiar el modelo.

Para publicar, autenticar GitHub y ejecutar los comandos indicados. Un repositorio privado requiere conceder acceso al profesor. No se facilitó su cuenta ni se envió invitación. Verificar posteriormente los enlaces de ambos idiomas y las descargas PDF desde una cuenta autorizada. Un README no requiere desplegar GitHub Pages.
