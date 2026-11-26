# Bitácora y evidencias

**26 de noviembre de2026 — comparación y presentación:** se revisó el control de apariencia persistente y se compararon Dynamic3DGaussians adaptado y4DGS con110 imágenes de optimización idénticas, diez instantes, semillas sin entrenar y view20 reservada. Dynamic ajusta la tabla inicial pero la pierde después; no se demuestra movimiento fiable. [Resultados, código fijado, recursos y comandos](dynamic-comparison.es.md). Se preparó una [presentación breve en inglés](../../presentations/progress-2026-11-26.en.pdf), PowerPoint editable, notas y dos ejemplos de código, con páginas del curso. Sin afirmar seguimiento físico ni rotaciones.

**24 de noviembre de 2026 — fondo invariable en el tiempo:** mismos tres instantes, entradas idénticas byte a byte y 200+6.000 pasos; solo los descendientes del volumen de siluetas reciben deformación temporal. Entrenamiento GPU 305,34 s; las funciones sobreviven a la densificación y los cinco atributos del fondo son invariantes en la auditoría del checkpoint. La variación estable en view20 baja unas 13 veces, pero empeora el PSNR de regiones cambiantes y la tabla aérea sigue incorrecta. [Comparaciones, controles, pruebas y propuesta con más instantes](actor-only.es.md). Sin afirmar flip fiel ni seguimiento físico.

[English](work-log.en.md) · Corte: 18 de noviembre de 2026

**24 de noviembre de 2026 — primer modelo temporal conjunto:** 42 imágenes de entrenamiento /3 de validación a tiempos0,5/9,1, con semillas canónicas del primer instante y37 máscaras de entrenamiento. Piloto3k y control separado6k; evaluación de checkpoints3k/6k de la misma trayectoria en3 tiempos supervisados y7 intermedios frente a tiempo congelado. Más duración mejora referencias observadas, pero forma central, interpolación y estabilidad del fondo siguen siendo deficientes. [Comparaciones, métricas, límites y siguientes pruebas](joint-temporal.es.md). Sin afirmar reconstrucción fiel ni seguimiento físico.

**24 de noviembre de 2026 — comprobación de tres instantes:** dos nuevos ajustes estáticos seguros de200+2.000 pasos a −0,85 s y −0,40 s amplían el de −0,60 s. Tabla reconocible en view20 de validación en los tres. Se conservan14 cámaras RGB; máscaras pequeñas13/14 del instante inicial se omiten del volumen/pérdida y sus métricas quedan no disponibles, no NaN. [Resultados, instantáneas, comandos y siguiente prueba temporal](multi-instant.es.md). Tres modelos independientes, sin interpolación temporal aprendida ni seguimiento.

**24 de noviembre de 2026 — fallo de integración confirmado:** la auditoría detecta cámara view20 coherente con el fondo y máscara anterior incompleta. CUDA corta a profundidad0,2 aunque Camera de Python usa0,01; se recortaba99,93% de las semillas de la tabla en view20. Escala uniforme4 conserva proyección y restaura visibilidad. El entrenamiento seguro hace reconocible la tabla en view20 (PSNR aproximado del deck15,75→22,91 dB). Se añade bloqueo de entradas inseguras y se corrige la interpretación anterior. [Evidencia, controles y reproducción](near-clip-fix.es.md). Sin resultado dinámico ni medición de rotaciones.

**24 de noviembre de 2026 — controles estáticos de un instante:** las 17 vistas no superan coherencia de siluetas/cajas con las cámaras y el instante actuales. Los desfases no resuelven tres vistas; la calibración con focales independientes se rechaza por degeneración. Un ajuste restringido a 14 vistas y un instante, con 13 máscaras de volumen, genera una tabla reconocible en entrenamiento, pero falla en view20 reservada. El control de geometría fija/color de grado cero no lo corrige. [Evidencias, imágenes y comandos](static-board.es.md). No se afirma movimiento aprendido ni seguimiento.

**24 de noviembre de 2026 — control del primer plano:** revisión de fases en 18 vistas y las 13 muestras completas de tres vistas cercanas; sincronización exacta todavía incierta. Control en RTX 4050 con entradas idénticas a la referencia, 200 pasos gruesos + 5.000 finos y pérdida adicional del primer plano solo en view19. Mejora el ajuste enmascarado de entrenamiento, pero aparece una mancha amplia y baja el PSNR completo reservado. [Resultados, comandos, comparaciones e hipótesis siguiente](foreground-trial.es.md). La cronología anterior conserva el contexto de su corte original.

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
| 2026-11-18 | Aclarar que es proyecto final y recibir apuntes del curso | [Mapa del curso](course-alignment.es.md), [huella del PDF](../evidence/course-context.json) | Enmarcar como proyecto final de Computer Vision y enlazar temas sin inventar una rúbrica |
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

### 20 de noviembre de 2026 — preparación de referencia real

Se eligieron DyNeRF `cut_roasted_beef` y Colab para la siguiente prueba de ejecución. Descarga/inspección de 20 vídeos sincronizados por los autores; cam00 reservada. Triangulación CPU con calibración fija: 3.390 puntos y error medio 0,710 px. Localización SIFT/PnP del fotograma 0 reservado: 961 inliers y diferencia angular 0,01094° respecto a calibración suministrada. Cuaderno Colab limitado preparado, sin ejecutar, artefacto compacto con licencia y protocolo bilingüe. Esto comprueba preparación geométrica, no entrenamiento dinámico ni calidad. [Comandos, evidencias, límites y objetivos de comprensión](dynerf.es.md).

## Cómo continuar

Usar la [plantilla de seguimiento](../templates/checkpoint.es.md). Cada resultado relevante debe tener fecha, comandos o commit, evidencia anterior y posterior, límites y siguiente criterio de aceptación. No atribuir trabajo no realizado ni cambiar mediciones anteriores sin explicar el motivo.
