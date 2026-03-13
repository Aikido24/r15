# Arquitectura completa del proyecto

## Objetivo general
Construir un sistema local que reciba una imagen de documento desde una URL, extraiga su texto, detecte tachones y correcciones visibles, valide sumas e inconsistencias, y devuelva un resultado estructurado para revision.

## Objetivos tecnicos
- Ejecutar el analisis en local usando `Ollama`.
- Procesar imagenes obtenidas desde internet por `URL`.
- Extraer texto y numeros con `OCR`.
- Detectar alteraciones visuales con un modelo multimodal.
- Validar reglas matematicas y de consistencia con codigo Python.
- Exponer todo mediante una API simple para consumir desde una interfaz web o cliente futuro.

## Stack recomendado

### Backend
- `Python 3.11+`
- `FastAPI`
- `Uvicorn`
- `Pydantic`

### IA local
- `Ollama`
- Modelo multimodal sugerido:
  - `qwen2.5-vl`
  - `minicpm-v`
  - `llava`

### OCR y vision
- `PaddleOCR`
- `OpenCV`
- `Pillow`

### Utilidades
- `httpx` para descarga de imagenes
- `python-multipart` si luego quieres subir archivos manualmente
- `pytest` para pruebas

## Arquitectura logica

### 1. Capa de entrada
Responsabilidad:
- recibir una `image_url`
- validar formato de entrada
- iniciar el pipeline

Componente:
- `FastAPI`

Entradas:
- URL de imagen
- criterios opcionales
- metadatos del documento si hicieran falta

### 2. Capa de adquisicion de imagen
Responsabilidad:
- descargar la imagen desde la URL
- validar que sea una imagen real
- rechazar archivos invalidos o demasiado grandes
- guardar temporalmente el archivo para procesamiento

Componente:
- modulo `services/image_fetcher.py`

Salida:
- ruta local temporal
- metadatos basicos de la imagen

### 3. Capa de preprocesado
Responsabilidad:
- mejorar calidad para OCR y analisis visual
- convertir a escala de grises si conviene
- ajustar contraste
- corregir inclinacion
- reducir ruido

Componente:
- modulo `services/preprocess.py`

Nota:
- esta capa puede activarse de forma gradual en el MVP

### 4. Capa OCR
Responsabilidad:
- extraer texto del documento
- detectar numeros, importes, fechas y etiquetas
- devolver bloques de texto o lineas detectadas

Componente:
- modulo `services/ocr_service.py`

Salida esperada:
- texto completo
- lineas detectadas
- coordenadas opcionales
- valores candidatos para reglas matematicas

### 5. Capa de analisis visual
Responsabilidad:
- enviar la imagen al modelo multimodal en `Ollama`
- pedir deteccion de:
  - tachones
  - correcciones manuales
  - sobrescrituras
  - campos posiblemente alterados
  - incoherencias visuales

Componente:
- modulo `services/ollama_service.py`

Regla importante:
- el modelo visual analiza indicios visuales, no debe ser la unica fuente para validar sumas

### 6. Capa de parsing y normalizacion
Responsabilidad:
- convertir texto OCR en datos estructurados
- limpiar formatos de numeros
- interpretar separadores como coma o punto
- identificar subtotal, impuestos y total

Componente:
- modulo `services/parser_service.py`

Salida esperada:
- objeto con campos estructurados
- lista de importes detectados
- campos dudosos o incompletos

### 7. Motor de reglas
Responsabilidad:
- validar reglas deterministicas del negocio
- comprobar sumas y coherencia entre campos
- marcar inconsistencias

Componente:
- modulo `services/rules_engine.py`

Ejemplos de reglas:
- `subtotal + impuesto = total`
- suma de lineas = subtotal
- campos repetidos deben coincidir
- valores negativos o improbables deben marcarse

### 8. Capa de consolidacion
Responsabilidad:
- combinar:
  - resultado OCR
  - hallazgos visuales
  - validaciones matematicas
- producir la respuesta final del sistema

Componente:
- modulo `services/report_builder.py`

Salida:
- JSON final con resumen y hallazgos

### 9. Capa de persistencia opcional
Responsabilidad:
- guardar resultados de ejecucion
- auditar imagen procesada, fecha y resultado
- permitir historico en el futuro

Opciones:
- al inicio: `JSON` o archivos locales
- despues: `SQLite` o `PostgreSQL`

## Flujo completo del sistema

1. El cliente llama al endpoint `/analyze` con una `image_url`.
2. La API valida la entrada.
3. Se descarga la imagen en una carpeta temporal.
4. Se ejecuta preprocesado basico.
5. Se lanza OCR sobre la imagen.
6. Se envia la imagen al modelo multimodal en `Ollama`.
7. Se parsean los datos OCR.
8. Se ejecutan reglas matematicas y de consistencia.
9. Se consolidan todos los hallazgos.
10. Se devuelve una respuesta JSON estructurada.

## Contrato de salida sugerido

```json
{
  "ok": false,
  "document_type": "factura",
  "source": {
    "image_url": "https://sitio.com/documento.jpg"
  },
  "ocr": {
    "raw_text": "Subtotal 1200 IVA 120 Total 1500",
    "fields": {
      "subtotal": 1200,
      "iva": 120,
      "total": 1500
    }
  },
  "visual_checks": {
    "tachones": true,
    "correcciones": true,
    "observaciones": [
      "Se observa una posible correccion en el campo total"
    ]
  },
  "rule_checks": [
    {
      "rule": "subtotal_mas_iva_igual_total",
      "passed": false,
      "message": "1200 + 120 no coincide con 1500"
    }
  ],
  "findings": [
    {
      "type": "alteracion_visual",
      "severity": "alta",
      "message": "Posible manipulacion en el total"
    },
    {
      "type": "inconsistencia_matematica",
      "severity": "alta",
      "message": "La suma no coincide con el total"
    }
  ],
  "summary": "El documento presenta alteraciones visuales y una inconsistencia en los importes."
}
```

## Estructura de carpetas recomendada

```text
r15/
|-- app/
|   |-- api/
|   |   |-- routes/
|   |   |   `-- analysis.py
|   |   `-- deps.py
|   |-- core/
|   |   |-- config.py
|   |   |-- logging.py
|   |   `-- exceptions.py
|   |-- models/
|   |   |-- requests.py
|   |   |-- responses.py
|   |   `-- domain.py
|   |-- services/
|   |   |-- image_fetcher.py
|   |   |-- preprocess.py
|   |   |-- ocr_service.py
|   |   |-- ollama_service.py
|   |   |-- parser_service.py
|   |   |-- rules_engine.py
|   |   `-- report_builder.py
|   |-- utils/
|   |   |-- files.py
|   |   |-- numbers.py
|   |   `-- prompts.py
|   `-- main.py
|-- data/
|   |-- samples/
|   |-- temp/
|   `-- outputs/
|-- tests/
|   |-- test_api.py
|   |-- test_rules.py
|   |-- test_parser.py
|   `-- fixtures/
|-- documentos/
|   |-- plan-implementacion.md
|   `-- arquitectura-proyecto.md
|-- scripts/
|   |-- run_dev.ps1
|   `-- smoke_test.py
|-- .env.example
|-- requirements.txt
`-- README.md
```

## Descripcion de carpetas

### `app/api/`
Define endpoints HTTP y controladores de entrada.

### `app/core/`
Configuracion central, logs, errores y valores comunes.

### `app/models/`
Modelos de entrada, salida y entidades internas.

### `app/services/`
Logica principal del sistema. Cada modulo tiene una responsabilidad concreta.

### `app/utils/`
Funciones auxiliares reutilizables, como manejo de archivos y parseo numerico.

### `data/samples/`
Imagenes de prueba del proyecto.

### `data/temp/`
Archivos descargados temporalmente desde URL.

### `data/outputs/`
Resultados del analisis en JSON o artefactos de depuracion.

### `tests/`
Pruebas unitarias y de integracion.

### `scripts/`
Scripts de ayuda para desarrollo local.

### `documentos/`
Documentacion funcional y tecnica del proyecto.

## Modulos minimos para arrancar

### `main.py`
Debe arrancar `FastAPI` y registrar rutas.

### `analysis.py`
Debe exponer el endpoint principal `/analyze`.

### `image_fetcher.py`
Debe descargar y validar imagenes.

### `ocr_service.py`
Debe ejecutar OCR y devolver texto.

### `ollama_service.py`
Debe enviar imagen y prompt al modelo local.

### `parser_service.py`
Debe extraer importes y campos relevantes.

### `rules_engine.py`
Debe validar operaciones matematicas y consistencia.

### `report_builder.py`
Debe consolidar la respuesta final.

## Endpoint inicial sugerido

### `POST /analyze`
Entrada:

```json
{
  "image_url": "https://sitio.com/documento.jpg"
}
```

Salida:
- estado del analisis
- texto extraido
- datos estructurados
- hallazgos visuales
- inconsistencias matematicas
- resumen final

## Orden recomendado para crear el proyecto

1. Crear estructura base de carpetas.
2. Crear `FastAPI` con endpoint `/health` y `/analyze`.
3. Implementar descarga de imagen por URL.
4. Integrar OCR.
5. Parsear importes y campos.
6. Crear reglas matematicas.
7. Integrar `Ollama`.
8. Consolidar respuesta final.
9. Agregar pruebas.
10. Mejorar preprocesado y precision.

## Decisiones recomendadas para el MVP
- No implementar scraping todavia.
- No guardar base de datos al inicio si no hace falta.
- Empezar con una sola clase de documento si es posible.
- Priorizar reglas matematicas simples y confiables.
- Usar `Ollama` como apoyo visual, no como verificador principal de sumas.

## Posibles ampliaciones futuras
- interfaz web para cargar URL o imagen manualmente
- soporte para multiples tipos de documento
- historial de analisis
- cola de procesamiento para lotes
- scraping automatico desacoplado
- exportacion de resultados a Excel o PDF
- puntuacion de confianza por hallazgo

## Recomendacion final
La primera version debe estar pensada como un pipeline modular. Si separas bien `descarga`, `OCR`, `analisis visual`, `reglas` y `reporte`, luego sera mucho mas facil mejorar precision, cambiar de modelo o agregar scraping sin rehacer el proyecto.
