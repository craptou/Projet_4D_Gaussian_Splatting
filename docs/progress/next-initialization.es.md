# Próximo experimento en terminal: remuestreo de inicialización

[English](next-initialization.en.md) · [Resultado de referencia](fixed-dynamic-pilot.es.md) · [Validación del lanzador](../evidence/next-initialization-validation.json)

El lanzador Windows está preparado para que lo ejecute el responsable. **El asistente no ha ejecutado el entrenamiento con la inicialización remuestreada.** Las comprobaciones de preparación y carga no son un resultado de optimización.

Desde PowerShell en el repositorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Continue-TrueSkate.ps1
```

`-CheckOnly` verifica archivos requeridos, configuración de referencia intacta, espacio libre, WSL e importaciones CUDA existentes sin entrenar. El experimento conserva las 8 cámaras de entrenamiento, cam13 reservada, 13 instantes, recortes, poses, imágenes, configuración del modelo y 200 pasos coarse + 2000 fine de la referencia. Reutiliza los entornos, sin instalar paquetes ni volver a entrenar la referencia.

La inicialización pasa de **1.115 a 8.920 puntos**. Se conservan los originales; las muestras adicionales interpolan posición/color sobre segmentos hacia seis puntos cercanos, con semilla 24. Son muestras sintéticas de inicialización, no geometría nueva medida ni triangulada. Los segmentos pueden cruzar límites de superficies. Cambian conjuntamente densidad y distribución espacial/de color; no es una ablación aislada del número de puntos. No añade puntos específicos de la tabla ni ponderación del primer plano.

Cuatro fases muestran progreso: comprobar GPU; preparar entradas y verificar imágenes idénticas; copiar a WSL, comprobar carga/proyección, entrenar y renderizar; comparar con la referencia existente. El entrenamiento muestra porcentajes, error, PSNR de imágenes de entrenamiento y número de puntos. Se informa del tiempo transcurrido cada 15 segundos durante fases silenciosas. Estimación inicial: 5–15 minutos, según arranque WSL, transferencia y carga GPU.

Cada ejecución crea `outputs/fixed-next-<fecha UTC>/`, con `input/`, `run/`, registros por fase y `comparison/`. El archivo final `test-cam13-comparison.jpg` muestra entrada / referencia / nuevo resultado; `summary.json` conserva las diferencias métricas. El comparador verifica píxeles idénticos en todas las imágenes objetivo evaluadas antes de comparar. Una mejora global no demuestra reconstrucción de la tabla: revisar imágenes y control de tiempo fijo. Se conservan datos originales y referencia. No se reanuda automáticamente una optimización interrumpida desde su estado del optimizador; los archivos parciales quedan disponibles.

Validación: `-CheckOnly` pasó con el entorno RTX 4050 existente; la preparación conservó 117 imágenes idénticas; pasaron 27 pruebas auxiliares, incluyendo conservación de geometría/color planos y rechazo de objetivos de evaluación modificados. Antes de entrenar también se comprueba la carga GPU con el número de puntos remuestreado. La calidad del experimento queda pendiente de la ejecución del responsable.
