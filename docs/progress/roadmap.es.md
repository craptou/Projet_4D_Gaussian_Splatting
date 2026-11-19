# Hitos y registro de riesgos

[English](roadmap.en.md) · Base: 18 de noviembre de 2026 · Sin fecha de entrega facilitada.

| ID | Hito | Estado | Evidencia de aceptación |
|---|---|---|---|
| M1 | Proyecto auditado, versionado y dependencia fijada | Completado localmente | Historial, auditoría y submódulos recursivos |
| M2 | Preparación automática del replay | Demostrada | 26 cortes candidatos, diagnóstico temporal y pruebas |
| M3 | Calibración móvil muestreada | Demostrada en la muestra | 175/175 imágenes en un modelo; recorte y máscaras explícitos |
| M4 | Poses de todas las imágenes y validación | Pendiente | Registro de imágenes necesarias, revisión de movimiento rápido, sensibilidad intrínseca y proyecciones de poses conocidas |
| M5 | Reproducción oficial de 4DGS | Bloqueada por el entorno | Importar extensiones CUDA; cargar escena oficial; 2 iteraciones gruesas + 10 finas; generar imágenes de prueba |
| M6 | Cargador con poses por imagen | Pendiente; depende de M4/M5 | Poses y tiempos sintéticos conocidos, regresión fija y vistas disjuntas |
| M7 | Reconstrucción dinámica y evaluación reservada | Pendiente; depende de M5/M6 | Modelo congelado, cam07 localizada, render sincronizado y PSNR/SSIM/LPIPS documentados |

M4 y la preparación del entorno pueden avanzar por separado. M5 debe aprobarse antes del entrenamiento dinámico propio; SfM muestreado no cumple el requisito de reproducción.

| Riesgo | Evidencia actual | Respuesta / control |
|---|---|---|
| Deriva del estado del replay | Puntuación aparece con diferencia ≤1 imagen | Revisar más eventos rápidos y conservar índices y desfases |
| Tratar cámara móvil como fija | Hipótesis comprobada en el cargador | Bloquear el flujo fijo y validar poses por imagen |
| Sesgo intrínseco o geométrico | Focal/punto principal compartidos; escala arbitraria | Sensibilidad del modelo, proyecciones y continuidad de trayectoria |
| Contaminación por primer plano dinámico | Máscaras rectangulares conservadoras | Revisar cobertura; conservar el skate para entrenamiento futuro |
| Confundir ajuste disperso con calidad final | Solo hay error de reproyección | Medir vistas nuevas únicamente tras evaluación real reservada |
| Recursos de cálculo limitados | RTX 4050 Laptop de 6 GB; entorno pendiente | Prueba oficial breve antes de trabajos largos |
| Falta de acceso del profesor | GitHub sin autenticar | Crear y subir repositorio privado; conceder acceso al profesor por separado |

No se asignan fechas, estimaciones de carga ni pesos de nota sin las restricciones del curso. Actualizar el seguimiento después de cada experimento, no solo antes de exponer.
