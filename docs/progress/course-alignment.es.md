# Vinculación con el curso — proyecto final

**Denominación facilitada por el responsable:** Computer Vision, CVI 26-2. Este repositorio documenta el **proyecto final del curso**, no un ejercicio independiente de gráficos. [English](course-alignment.en.md)

## Fuente y alcance

Documento aportado localmente: **CVI 26-2 Prompts**, atribuido a **Pablo Figueroa** en la página 1; archivo `CVI 26-2 Prompts (3).pdf`, 46 páginas. Las referencias utilizan la **numeración del PDF desde 1**, incluida la portada. La [huella de la fuente y el índice](../evidence/course-context.json) identifican la copia revisada. El PDF completo se conserva localmente; Git versiona esta interpretación con páginas de referencia, sin redistribuir todo el material docente.

El documento se presenta como una síntesis semanal de temas e incluye contenidos matemáticos, de imagen y de gráficos. Se mantiene el nombre Computer Vision indicado por el responsable y se explicitan las conexiones con los temas gráficos, sin equiparar ambos campos. En esta copia no se encontró un enunciado del proyecto final, pesos de evaluación, fecha de entrega ni formato obligatorio de exposición. El responsable indicó por separado que el seguimiento se califica; es una restricción comunicada por él, no una cita del PDF.

## Aplicación de los temas del curso

| Tema del documento | Páginas PDF | Aplicación al proyecto | Evidencia actual / demostración pendiente |
|---|---|---|---|
| Álgebra lineal, coordenadas homogéneas y geometría proyectiva | 3–4 | Representar transformaciones mundo-cámara y reproyectar puntos en imágenes | `[R|T]` por imagen, controles de rotación y convenciones explícitas |
| Viewing: viewport, cámara y perspectiva | 12–15 | Distinguir intrínsecos/extrínsecos y ajustar coordenadas tras el recorte | Modelo compartido y punto principal `(296,540)`; faltan validación con poses conocidas y sensibilidad |
| Imágenes ráster y color | 5–6 | Tratar las grabaciones como matrices de píxeles y documentar tamaño/codificación | Original 720 × 1280 y recorte 592 × 820; las métricas futuras deben fijar el espacio de color |
| Procesamiento de señales, muestreo, filtrado y reconstrucción | 18–27 | Conservar índices comunes y razonar sobre aliasing temporal, interpolación y remuestreo | Sin remuestreo independiente; evento con diferencia ≤1 imagen; sincronización completa no demostrada |
| Pipeline gráfico, rasterización, visibilidad y antialiasing | 15–18 | Explicar la futura proyección/composición de Gaussianas en una imagen nueva | Etapa 4DGS pendiente; la nube actual no es un modelo dinámico rasterizado |
| Estructuras de datos para gráficos | 32–35 | Comparar representaciones y discutir memoria y visibilidad | Existen puntos dispersos y grafo de cámaras; Gaussianas aprendidas y comparación de rendimiento pendientes |
| Curvas, derivadas y continuidad | 40–44 | Analizar trayectorias de cámara y movimiento temporal | Siete poses por pasaje; no se presenta una interpolación spline como medición real |
| Sombreado, texturas y transporte físico de luz | 9–11, 27–32, 35–40 | Discutir apariencia dependiente de la vista y síntesis aprendida frente a transporte explícito | Comparación conceptual; no se afirma implementar BRDF, texturas, ray tracing ni path tracing propios |

SfM, SIFT, bundle adjustment y 4DGS son técnicas del proyecto basadas en estos conceptos. El PDF no exige explícitamente todos esos algoritmos. Se reconoce la reutilización de PyCOLMAP y 4DGS oficial; las contribuciones propias están en preparación de datos, comprobaciones de cámaras, diseño experimental y herramientas de evaluación.

## La pregunta de visión y la etapa gráfica

La parte **inversa** estima cámaras y una representación de escena a partir de imágenes. La parte **directa** utiliza esa representación para sintetizar píxeles desde una cámara nueva en un instante elegido. El proyecto final debe explicar y validar la conexión entre ambas.

Para un punto mundial `X`, el modelo es `p ~ K[R|T]X`. Recortar cambia el origen de las coordenadas de imagen y, por tanto, el punto principal. La cámara móvil necesita `[R(c,t)|T(c,t)]`; una sola pose constante contradiría la captura. La etapa futura proyectará Gaussianas condicionadas por el tiempo. No debe presentarse como una implementación de todo el pipeline tradicional de triángulos ni de un trazador físico de caminos.

## Demostraciones vinculadas al curso

Son **propuestas para este proyecto**, no una rúbrica extraída del documento:

1. Explicar un ejemplo mundo-cámara-imagen y el efecto del recorte sobre `K`.
2. Comparar la hipótesis de cámara fija con las trayectorias recuperadas y justificar por qué hay que adaptar el cargador.
3. Mostrar un evento común entre vistas y explicar los límites del acuerdo de una imagen.
4. Separar la evidencia del fondo disperso de la futura reconstrucción dinámica y explicar representación y visibilidad.
5. Cuando funcione el entrenamiento, variar cámara y tiempo por separado y comparar cam07 con sus renders.
6. Aportar comandos, configuración, fallos y bitácora fechada para evaluar el progreso más allá de la apariencia visual.

## Información de evaluación aún necesaria

No se han establecido el enunciado exacto, los pesos, la duración de exposición, la fecha de entrega, las reglas de grupo/autoría ni posibles exigencias de implementación desde cero. Se añadirán cuando estén disponibles; la hoja de ruta propia no debe presentarse como la rúbrica oficial del profesor. Esta actualización documental no cambia las mediciones existentes.
