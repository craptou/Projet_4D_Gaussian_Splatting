# Validación del material de seguimiento

[English](validation.en.md) · Verificado el 18 de noviembre de 2026

- La batería existente superó **19 pruebas**, incluida extracción de vídeo sintético y exclusión de la vista reservada.
- Se generaron **12 diapositivas inglesas y 12 españolas** desde la misma fuente bilingüe, con notas, PDF y PPTX editable.
- Se decodificaron y renderizaron todas las páginas PDF. Se inspeccionaron mosaicos y páginas individuales para comprobar legibilidad y recortes.
- Se verificaron número de diapositivas, límites de formas, evidencias y notas del PPTX. No se comprobó una renderización independiente en PowerPoint.
- Se comprobaron todos los enlaces relativos del material. El script permite repetir el control y verifica también la separación de vistas y el total registrado.
- Las figuras proceden de capturas observadas y del modelo disperso conservado. El gráfico español representa los mismos puntos y trayectorias con etiquetas traducidas.
- Las evidencias registran 175/175 imágenes muestreadas, 8767 puntos, 8377 puntos compartidos y una imagen de diferencia en el evento de puntuación. No implican entrenamiento 4DGS ni métricas reservadas.
- Las dependencias superan `pip check`, los scripts compilan y no hay errores de espacios en Git.
- Tras recibir los apuntes se regeneraron las presentaciones como proyecto final de Computer Vision — CVI 26-2 y se añadió el mapa bilingüe con páginas. Si el original está disponible localmente, se comprueban su huella y sus 46 páginas; no es necesario para clonar o consultar el material.
- Vídeos, modelos, bases de datos y conjuntos completos siguen excluidos de Git. El paquete solo incluye figuras pequeñas, evidencias estructuradas, texto y presentaciones.

Repetir `python scripts/validate_review_docs.py` al cambiar enlaces o regenerar diapositivas. Repetir pruebas funcionales cuando lo requieran cambios de código. Publicar es una etapa distinta: no había autenticación de GitHub al preparar este material.
