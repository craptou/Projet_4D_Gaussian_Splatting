# Hitos y registro de riesgos

[English](roadmap.en.md) · Base: 18 de noviembre de 2026 · Sin fecha de entrega facilitada.

**Proyecto final: Computer Vision — CVI 26-2.** El [mapa del curso](course-alignment.es.md) relaciona etapas y apuntes. La tabla siguiente es el plan de validación propuesto por el proyecto, no la rúbrica oficial del profesor.

| ID | Hito | Estado | Evidencia de aceptación |
|---|---|---|---|
| M1 | Proyecto auditado, versionado y dependencia fijada | Completado localmente | Historial, auditoría y submódulos recursivos |
| M2 | Preparación automática del replay | Demostrada | 26 cortes candidatos, diagnóstico temporal y pruebas |
| M3 | Calibración móvil muestreada | Demostrada en la muestra | 175/175 imágenes en un modelo; recorte y máscaras explícitos |
| M4 | Poses completas y validación | Cobertura demostrada; validación parcial | 2725/2725 aceptadas, referencias intactas y sin saltos marcados; falta revisar soporte menor e intrínsecos |
| M5 | Reproducción oficial de 4DGS | Bloqueada por el entorno | Importar extensiones CUDA; cargar escena oficial; 2 iteraciones gruesas + 10 finas; generar imágenes de prueba |
| M6 | Cargador con poses por imagen | Pendiente; depende de M4/M5 | Poses y tiempos sintéticos conocidos, regresión fija y vistas disjuntas |
| M7 | Reconstrucción dinámica y evaluación reservada | Pendiente; depende de M5/M6 | Modelo congelado, cam07 localizada, render sincronizado y PSNR/SSIM/LPIPS documentados |

M4 y la preparación del entorno pueden avanzar por separado. M5 debe aprobarse antes del entrenamiento dinámico propio; SfM muestreado no cumple el requisito de reproducción.

Para la revisión final, preparar además un ejemplo mundo-cámara-imagen (Viewing, PDF pp. 12–15), justificar muestreo espacial/temporal (pp. 5–6, 18–27) y distinguir trayectorias muestreadas (pp. 40–44) de poses interpoladas o medidas a frecuencia completa. Comparar la futura rasterización de Gaussianas con el pipeline del curso (pp. 15–18). Son demostraciones propuestas; el enunciado final puede añadir o cambiar exigencias.

| Riesgo | Evidencia actual | Respuesta / control |
|---|---|---|
| Deriva del estado del replay | Puntuación aparece con diferencia ≤1 imagen | Revisar más eventos rápidos y conservar índices y desfases |
| Tratar cámara móvil como fija | Hipótesis comprobada en el cargador | Bloquear el flujo fijo y validar poses por imagen |
| Sesgo intrínseco o geométrico | Focal/punto principal compartidos; escala arbitraria | Sensibilidad del modelo, proyecciones y continuidad de trayectoria |
| Contaminación por primer plano dinámico | Máscaras rectangulares conservadoras | Revisar cobertura; conservar el skate para entrenamiento futuro |
| Confundir ajuste disperso con calidad final | Solo hay error de reproyección | Medir vistas nuevas únicamente tras evaluación real reservada |
| Recursos de cálculo limitados | RTX 4050 Laptop de 6 GB; entorno pendiente | Prueba oficial breve antes de trabajos largos |
| Acceso del profesor y publicación | Repositorio público publicado el 19 de noviembre; `main` enviado | Compartir el enlace y mantener enlaces/documentación actualizados |

No se asignan fechas, estimaciones de carga ni pesos de nota sin las restricciones del curso. Actualizar el seguimiento después de cada experimento, no solo antes de exponer.
