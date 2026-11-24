# Control de entrenamiento más largo: lanzador preparado

[English](duration-control.en.md) · [Evidencia de validación](../evidence/duration-launcher-validation.json) · [Experimento anterior de inicialización](resampling-result.es.md)

**Ejecución del responsable completada:** [progresión medida y resultados visuales](duration-result.es.md). Las instrucciones y validación siguientes describen el control preparado; la evidencia de validación enlazada es anterior a la optimización. El responsable propuso este experimento porque el ensayo de inicialización no respondía a si 2.000 pasos eran suficientes.

Desde PowerShell en el repositorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Train-TrueSkate-Long.ps1
```

`-CheckOnly` comprueba hashes de entradas/configuración originales, imágenes necesarias, espacio libre e importaciones WSL/CUDA existentes sin entrenar. El lanzador utiliza los **1.115 puntos iniciales originales**, no el remuestreo, con las mismas 8 cámaras de entrenamiento, cam13 reservada, 104 imágenes de entrenamiento y 13 reservadas en 0,4 segundos. Inicia una trayectoria nueva con la semilla upstream y conserva los modelos anteriores.

La configuración hereda el primer ensayo y solo sustituye `OptimizationParams.iterations=10000`. Antes de entrenar se comprueba la configuración efectiva de MMCV. Se conservan 200 pasos coarse, programas de tasas de aprendizaje, errores, red, recorte, poses, imágenes y programa de densificación, que termina en el paso 1.300. Los pasos adicionales optimizan la representación existente; no amplían la fase de crecimiento de puntos. Se mantiene el programa SH original: grado 2 en el paso fine 2.000 y grado máximo 3 en 5.000/10.000.

Un único entrenamiento guarda y evalúa modelos a los **2.000, 5.000 y 10.000 pasos fine**. El terminal muestra progreso, error/PSNR de entrenamiento y número de puntos, con tiempo transcurrido cada 15 segundos. Después de optimizar, se renderizan todos los modelos guardados para la vista reservada y cam08, restaurando el grado SH correspondiente. Estimación inicial: 10–20 minutos, según arranque y carga del equipo. Se reutilizan los entornos sin instalar paquetes.

Cada ejecución crea `outputs/fixed-duration-<fecha UTC>/`. La carpeta final `comparison/` contiene:

- `test-cam13-comparison.jpg` y `train-cam08-comparison.jpg`: grabación / 2.000 / 5.000 / 10.000.
- `progression.png`: curvas PSNR de imagen completa y región cambiante del objetivo.
- `progression.json` y `.csv`: métricas de cada modelo, incluyendo SSIM y control de tiempo fijo.

El comparador verifica píxeles objetivo idénticos entre modelos. La región cambiante no es segmentación de la tabla. Evaluar si la tabla se vuelve reconocible y mejora su movimiento, junto con el fondo y el control de tiempo fijo. Un aumento global no valida por sí solo el truco. La comparación principal usa modelos de la misma trayectoria; no se presupone identidad exacta con el modelo anterior de 2.000 pasos.

Validación sin optimización: pasaron `-CheckOnly`, la carga/proyección GPU real con la configuración heredada, la comparación de configuración efectiva, las pruebas de argumentos de guardado/evaluación y 31 pruebas auxiliares. El generador de comparaciones/gráficas se comprobó con imágenes de referencia organizadas como archivos de prueba; **esas copias no son resultados de 5.000/10.000 pasos**. Se conservan modelos/registros escritos si se interrumpe el proceso; el lanzador no reanuda automáticamente el estado del optimizador.
