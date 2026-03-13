# Plan de implementacion del sistema

## Objetivo
Construir un sistema local que reciba imagenes desde una URL, analice documentos con texto usando `Ollama`, detecte `tachones`, `correcciones` e `inconsistencias`, y valide si las `sumas` y `totales` son correctos.

## Etapa 1: Definir alcance y reglas
### Objetivo
Definir exactamente que va a revisar el sistema.

### Tareas
- Identificar los tipos de documentos a analizar.
- Definir criterios de revision:
  - tachones
  - correcciones
  - sobrescrituras
  - inconsistencias en datos
  - errores en sumas y totales
- Definir formato de salida esperado.
- Reunir imagenes de ejemplo para pruebas.

### Entregable
- Documento con reglas de negocio y ejemplos de casos validos e invalidos.

## Etapa 2: Preparar entorno base
### Objetivo
Montar la base tecnica del proyecto.

### Tareas
- Crear backend con `Python + FastAPI`.
- Instalar y probar `Ollama`.
- Seleccionar un modelo multimodal:
  - `qwen2.5-vl`
  - `minicpm-v`
  - `llava`
- Integrar OCR, preferiblemente `PaddleOCR`.
- Añadir librerias auxiliares:
  - `OpenCV`
  - `Pillow`
  - `requests` o `httpx`
  - `pydantic`

### Entregable
- API local funcionando con un endpoint de prueba.

## Etapa 3: Ingesta de imagenes por URL
### Objetivo
Permitir que el sistema reciba imagenes desde internet.

### Tareas
- Crear endpoint que reciba `image_url`.
- Descargar la imagen temporalmente.
- Validar:
  - que la URL exista
  - que sea una imagen
  - tamano maximo permitido
  - formatos soportados
- Preparar el archivo para procesamiento.

### Entregable
- Flujo estable de `URL -> descarga -> archivo temporal`.

## Etapa 4: Extraccion de texto con OCR
### Objetivo
Leer el contenido textual del documento.

### Tareas
- Procesar la imagen con OCR.
- Extraer:
  - subtotal
  - impuestos
  - total
  - importes parciales
  - fechas
  - otros campos relevantes
- Normalizar numeros y separadores.
- Guardar resultados en una estructura clara.

### Entregable
- JSON con texto detectado y valores numericos extraidos.

## Etapa 5: Analisis visual con Ollama
### Objetivo
Detectar problemas visuales en el documento.

### Tareas
- Enviar la imagen al modelo multimodal.
- Solicitar deteccion de:
  - tachones
  - correcciones manuales
  - sobrescrituras
  - numeros alterados visualmente
  - zonas sospechosas
- Forzar salida estructurada en JSON.

### Entregable
- JSON con hallazgos visuales.

## Etapa 6: Validacion matematica y de consistencia
### Objetivo
Comprobar con reglas de negocio si los datos son correctos.

### Tareas
- Validar operaciones como:
  - `subtotal + impuesto = total`
  - suma de lineas = subtotal
  - coherencia entre campos repetidos
- Detectar datos faltantes o improbables.
- Separar errores en categorias:
  - visuales
  - textuales
  - matematicos

### Entregable
- Modulo Python con validaciones deterministicas.

## Etapa 7: Consolidacion del resultado
### Objetivo
Unir todos los analisis en una sola respuesta.

### Tareas
- Combinar resultados de OCR, Ollama y reglas.
- Generar salida final con:
  - `cumple`
  - `hallazgos`
  - `campos_extraidos`
  - `resumen`
- Clasificar severidad de cada hallazgo.

### Entregable
- Respuesta JSON final estandarizada.

## Etapa 8: Construccion del MVP
### Objetivo
Tener una primera version usable de punta a punta.

### Tareas
- Crear endpoint principal de analisis.
- Procesar imagen desde URL.
- Ejecutar OCR.
- Analizar visualmente con Ollama.
- Validar sumas e inconsistencias.
- Devolver un reporte final.

### Entregable
- MVP funcional en local.

## Etapa 9: Evaluacion y ajuste
### Objetivo
Medir precision y mejorar calidad.

### Tareas
- Crear dataset de prueba con casos:
  - documento limpio
  - documento con tachones
  - documento con correcciones
  - documento con total incorrecto
  - documento con OCR dificil
- Medir:
  - precision OCR
  - precision visual
  - falsos positivos
  - falsos negativos
- Ajustar prompts, OCR y reglas.

### Entregable
- Informe de resultados y lista de mejoras.

## Etapa 10: Robustez y mejoras tecnicas
### Objetivo
Hacer el sistema estable y mantenible.

### Tareas
- Anadir preprocesado de imagen:
  - escala de grises
  - contraste
  - binarizacion
  - correccion de inclinacion
- Manejar errores y timeouts.
- Anadir logs del pipeline.
- Reintentos si OCR o analisis fallan.
- Considerar cache para imagenes repetidas.

### Entregable
- Version mas robusta del sistema.

## Etapa 11: Integracion futura de scraping
### Objetivo
Agregar obtencion automatica de imagenes mas adelante.

### Tareas
- Crear modulo separado de scraping.
- Mantener desacoplado el origen de datos del analisis.
- Guardar metadatos:
  - URL origen
  - fecha de captura
  - fuente
- Evitar mezclar scraping con validacion.

### Entregable
- Sistema preparado para integrar scraping sin romper el flujo principal.

## Orden recomendado de implementacion
1. Definir criterios y casos reales.
2. Montar `FastAPI + Ollama + OCR`.
3. Recibir imagen por URL.
4. Extraer texto y numeros con OCR.
5. Validar sumas con codigo.
6. Analizar tachones y correcciones con Ollama.
7. Consolidar respuesta final.
8. Probar MVP.
9. Ajustar precision.
10. Integrar scraping despues.

## MVP minimo recomendado
El MVP deberia hacer lo siguiente:
- recibir una `URL` de imagen
- descargar la imagen
- extraer texto con OCR
- detectar importes
- validar sumas y totales
- pedir a `Ollama` deteccion de tachones y correcciones
- devolver un JSON final con hallazgos

## Riesgos principales
- OCR poco preciso por mala calidad de imagen
- documentos con formatos muy distintos
- texto pequeno o borroso
- correcciones visuales sutiles dificiles de detectar
- falsas alarmas del modelo multimodal

## Recomendacion clave
Usar `Ollama` para el analisis visual y usar `Python` para las validaciones matematicas. No conviene dejar la comprobacion de sumas solo al modelo.
