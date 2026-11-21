# Demostración de la escena 4D — 20 de noviembre de 2026

[English](4d-demonstration.en.md)

Las comparaciones de imágenes evalúan el modelo, pero no muestran por sí solas control independiente de espacio y tiempo. La representación contiene gaussianas 3D canónicas (`point_cloud.ply`) y una red de deformación temporal (`deformation.pth` y estado asociado). Un visor PLY estático omitiría la deformación. Se demuestra el modelo guardado de **10.799 gaussianas, etapa 3000**, sin volver a entrenar.

## Visor local

Desde PowerShell en el repositorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Open-4DScene.ps1
```

Abrir **http://127.0.0.1:8765** cuando esté listo. Reutiliza entorno CUDA/modelo, sin instalar paquetes. El servidor calcula cada vista/tiempo solicitados en GPU; no busca fotogramas precalculados. El navegador muestra esos renders JPEG.

- **Animar tiempo:** cam00 fija y escena en movimiento, a cámara lenta ×3.
- **Desplazar cámara:** tiempo congelado y cámara virtual entre cam01/cam20; posición lineal y rotación SLERP. Las posiciones intermedias son nuevas vistas solicitadas.
- Controles independientes. El botón de detener cierra el visor y libera el proceso GPU. Servicio solo en loopback.

Reconstrucción frontal parcial, no escaneo a 360°. Fotogramas aprendidos 0–29 (0,967 segundos entre extremos). Sin afirmar reconstrucción posterior, tiempos más largos ni trayectorias físicas correctas. Los centros gaussianos cambian con el tiempo aprendido, pero no constituyen verdad terreno de movimiento.

## Clips compartibles

| Clip | Fijo | Variable |
|---|---|---|
| [Tiempo](../assets/4d-demo-time.mp4) | Cámara cam00 | Tiempo 0 → 29/300; 30 renders en 3 segundos |
| [Cámara con tiempo congelado](../assets/4d-demo-view.mp4) | Fotograma 14, tiempo 14/300 | Posición/rotación de cámara; 60 renders en 4 segundos |

768 × 576, calculados con el modelo congelado. Unos **2,4 MiB** entre ambos; derivados pequeños permitidos explícitamente, no vídeos originales. Reproducir en el entorno GPU: `scripts/view_4d_reference.py --model MODEL --export OUTPUT`.

El README incluye vistas previas GIF de **360 × 270, 10 FPS**, convertidas de estos clips. Muestran cambios de tiempo/vista directamente en GitHub sin instalar GPU. Son grabaciones; GitHub no aloja la aplicación interactiva Python/CUDA. Reducción de resolución/paleta solo para presentación, fuera de la evaluación numérica.

## Comprobaciones

Acceso Windows a WSL mediante localhost. Peticiones reales devolvieron JPEG 768 × 576; variar tiempo con cámara fija y variar cámara con tiempo fijo cambiaron los píxeles. Tiempo no finito rechazado con HTTP 400. Interfaz cargada en Chrome sin interfaz y revisada visualmente. [Diagnósticos](../evidence/4d-demonstration-2026-11-20.json). Movimiento aprendido o diferencias de imagen no demuestran por sí solos exactitud de geometría dinámica.

Imágenes y renders derivados: Neural 3D Video Synthesis (Li et al., CVPR 2022), [datos originales](https://github.com/facebookresearch/Neural_3D_Video), CC-BY-NC-4.0. Modelo/datos fuera de Git; código, diagnósticos y clips pequeños versionados. La apertura automática del navegador fue bloqueada por controles de ejecución; se proporciona el enlace para abrirlo manualmente.
