# Bitácora y evidencias

[English](work-log.en.md) · Corte: 18 de noviembre de 2026

Estas entradas se basan en Git y en artefactos experimentales conservados. Documentan cortes reales, no una actividad semanal continua. Los commits pueden inspeccionarse con `git show <hash>` después de clonar el repositorio.

| Fecha | Problema / acción | Evidencia y resultado | Interpretación / siguiente paso |
|---|---|---|---|
| 2026-10-19 | Auditar el equipo, fijar la dependencia oficial e iniciar el proyecto | `b24c12f`, `34d109d`; [auditoría inicial](../system-report.md) | GPU identificada; entorno de compilación CUDA ausente |
| 2026-10-19 | Crear extracción, validación y envoltorios seguros de cámara fija | `a8206c9`; 10 pruebas iniciales superadas | Preparación en CPU funcional; flujo completo aún no validado |
| 2026-10-19 | Inspeccionar las hipótesis de cámara fija y estudiar poses móviles | `774e1b5`; [análisis del código](../moving-camera-plan.md) | Impedir el uso silencioso de una pose fija para una secuencia móvil |
| 2026-10-19 | Corregir codificación y campos de hardware de la auditoría | `d036ce6` | Informe legible; no implica entrenamiento en GPU |
| 2026-11-18 | Recibir grabación y ocho cortes manuales; automatizar segmentación | `a23b464`; [revisión de captura](../capture-review-2026-11-18.md) | 26 pasajes de 109 imágenes; 16 pruebas |
| 2026-11-18 | Recortar, enmascarar y ejecutar la prueba dispersa inicial | `c73a1f9`; [informe de poses](../pose-pilot-2026-11-18.md) | 33/42 imágenes registradas; investigar cobertura y solapamiento |
| 2026-11-18 | Añadir vistas intermedias sin relajar umbrales de reconstrucción | `c73a1f9`, `64a3fc1`; [JSON del corte](../evidence/checkpoint-2026-11-18.json) | 175/175 imágenes, 8767 puntos, 0,473 px; 19 pruebas |
| 2026-11-18 | Comprobar aparición del marcador y reservar cam07 | `c73a1f9`; documentación del experimento | Diferencia de una imagen; evaluación reservada pendiente |
| 2026-11-18 | Preparar documentación bilingüe, evidencias y presentaciones | Commits actuales; `git log -- presentations docs/progress` | Publicar un corte revisable y continuar el registro fechado |
| 2026-11-18 | Aclarar que es proyecto final y recibir CVI 26-2 Prompts | [Mapa del curso](course-alignment.es.md), [huella del PDF](../evidence/course-context.json) | Enmarcar como proyecto final de Computer Vision y enlazar temas sin inventar una rúbrica |
| 2026-11-18 | Localizar las otras 2550 imágenes e investigar 31 fallos iniciales | `50b2fc3`; [experimento completo](fullrate.es.md), [evidencia](../evidence/fullrate-2026-11-18.json) | 2725/2725 aceptadas sin cambiar mapa/referencias; 132 casos de soporte menor para revisar; 25 pruebas |
| 2026-11-19 | Recibir remoto, inspeccionar y publicar el historial existente | [Repositorio GitHub](https://github.com/craptou/Projet_4D_Gaussian_Splatting); `git push -u origin main` | Remoto vacío, envío normal correcto; visibilidad pública y rama `main` verificadas |

## Decisiones respaldadas por el historial

- Conservar intacto el submódulo oficial; desarrollar scripts y envoltorios propios.
- Sustituir cortes manuales desiguales por segmentación basada en el cursor.
- Estimar poses por imagen con el fondo, porque la cámara se mueve.
- Añadir solapamiento antes de debilitar los umbrales de reconstrucción.
- Excluir cam07 de la optimización geométrica y comprobar su tiempo por separado.
- Separar el éxito del registro disperso del entrenamiento 4DGS aún no ejecutado.

## Fallos y bloqueos pendientes

La primera prueba no registró nueve imágenes. Las vistas intermedias resolvieron ese problema; el experimento completo posterior se documenta por separado. El audio no permitió alinear con confianza. Faltan el entorno CUDA y la reproducción oficial. La publicación pendiente del 18 de noviembre se realizó el día 19 mediante Git, aunque la herramienta opcional GitHub CLI sigue sin sesión. Ningún comando fallido se cuenta como hito completado.

## Cómo continuar

Usar la [plantilla de seguimiento](../templates/checkpoint.es.md). Cada resultado relevante debe tener fecha, comandos o commit, evidencia anterior y posterior, límites y siguiente criterio de aceptación. No atribuir trabajo no realizado ni cambiar mediciones anteriores sin explicar el motivo.
