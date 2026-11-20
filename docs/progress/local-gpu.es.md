# Ejecución GPU local — 20 de noviembre de 2026

[English](local-gpu.en.md)

Colab no funcionó para el responsable (no se aportó el error). Se eligió la RTX 4050 local. WSL estaba instalado sin distribución Linux. Se instaló Ubuntu 22.04 en WSL2, conservando el controlador NVIDIA de Windows. Compilador/cabeceras CUDA 12.1 y Python 3.10 instalados en Linux. Un kernel CUDA compilado para sm_89 devolvió el resultado esperado (285); PyTorch 2.1.2-cu121 detectó la RTX 4050.

**No ha comenzado el entrenamiento 4DGaussians.** El lanzador del terminal completará dependencias Python, extensiones CUDA, entrenamiento y renderizado, mostrando la evolución. La incompatibilidad temporal con NumPy 2 se resuelve fijando NumPy 1.26.4 en el instalador. Entorno de compatibilidad diferente del original.

Desde PowerShell en el repositorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-LocalGPU.ps1
```

La política de ejecución se modifica solo para ese proceso hijo. El lanzador retoma la instalación, reutiliza PyTorch o el instalador completo si están disponibles, compila extensiones, comprueba el cargador y ejecuta 2 pasos coarse + 10 fine, seguidos de 30 renders reservados. Muestra registros y tiempo transcurrido cada 15 segundos. Las estimaciones son aproximadas. Impide dos lanzamientos simultáneos y se detiene ante errores indicando el registro. La opción `-CheckOnly`, probada localmente, verifica WSL/compilador/GPU/rutas sin instalar ni entrenar.

Entrada reducida preparada: entrenar con cam01, cam05, cam12 y cam20; reservar cam00. Fotogramas 0–29 a 1352 × 1014, conservando tiempo `índice / 300`. Inicialización dispersa previa de 3.390 puntos, sin cam00. Vídeos enlazados sin duplicar almacenamiento. Código en `/root/skate4d/project` para compilar; datos/resultados en el repositorio Windows.

Cada ejecución escribe `outputs/dynerf-local-<fecha UTC>/`, con `setup.log` y `execution.log`. Solo tras éxito se producirán `report.json`, `comparison.jpg` y registros detallados. Doce pasos comprueban ejecución, no convergencia ni calidad útil.

Se comprobaron sintaxis, salida en directo, propagación de errores, tiempo límite y lanzador de solo verificación. La secuencia GPU completa no se ha ejecutado. El terminal del usuario mantiene el proceso sin depender de una sesión de herramientas del asistente.
