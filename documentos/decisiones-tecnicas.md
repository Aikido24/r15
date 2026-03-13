# Decisiones tecnicas

## Objetivo
Este documento registra decisiones tecnicas del proyecto para mantener contexto, justificar elecciones y evitar reevaluar lo mismo en cada etapa del desarrollo.

## Como usar este documento
- Registrar decisiones de arquitectura, librerias, modelos y flujo de trabajo.
- Anotar el motivo de cada eleccion.
- Indicar impacto, alcance y si la decision es temporal o definitiva.
- Actualizar cuando una decision cambie.

## Formato sugerido

```md
## [Decision]
- Fecha:
- Estado: propuesta | adoptada | reemplazada
- Area:
- Decision:
- Motivo:
- Impacto:
- Alternativas consideradas:
```

## Registro actual

## Backend principal con `FastAPI`
- Fecha: 2026-03-12
- Estado: adoptada
- Area: backend
- Decision: usar `FastAPI` como framework principal de API.
- Motivo: es simple, moderno, compatible con `Pydantic` y adecuado para exponer endpoints del pipeline de analisis.
- Impacto: la estructura del proyecto gira alrededor de rutas, modelos y servicios Python.
- Alternativas consideradas: `Flask`, `Django`.

## Gestion del proyecto Python con `pyproject.toml`
- Fecha: 2026-03-12
- Estado: adoptada
- Area: entorno
- Decision: usar `pyproject.toml` como archivo principal de dependencias y configuracion del proyecto.
- Motivo: cumple el papel mas cercano a `package.json` en este proyecto y deja una base mas ordenada que `requirements.txt` solo.
- Impacto: la instalacion y evolucion del proyecto se apoyan en este archivo.
- Alternativas consideradas: `requirements.txt` como archivo unico.

## Uso de entorno virtual local `.venv`
- Fecha: 2026-03-12
- Estado: adoptada
- Area: entorno
- Decision: instalar dependencias dentro de `.venv` en la raiz del proyecto.
- Motivo: aislar paquetes del sistema y evitar conflictos entre proyectos.
- Impacto: los comandos del proyecto deben usar el Python del entorno virtual.
- Alternativas consideradas: instalacion global.

## IA local con `Ollama`
- Fecha: 2026-03-12
- Estado: adoptada
- Area: inteligencia artificial
- Decision: ejecutar el modelo visual localmente con `Ollama`.
- Motivo: permite operar en local, simplifica pruebas iniciales y evita depender de APIs externas.
- Impacto: el sistema requiere el runtime de `Ollama` y al menos un modelo multimodal descargado.
- Alternativas consideradas: APIs cloud de vision o LLM.

## Modelo inicial `qwen2.5vl:7b`
- Fecha: 2026-03-12
- Estado: adoptada
- Area: inteligencia artificial
- Decision: usar `qwen2.5vl:7b` como primer modelo multimodal para el MVP.
- Motivo: ofrece una relacion razonable entre capacidad y ejecucion local para analizar imagenes con texto.
- Impacto: requiere una descarga aproximada de `6 GB` y sera el modelo base para pruebas iniciales.
- Alternativas consideradas: `minicpm-v`, `llava`.

## OCR con `PaddleOCR`
- Fecha: 2026-03-12
- Estado: adoptada
- Area: OCR
- Decision: usar `PaddleOCR` para extraccion de texto.
- Motivo: es una opcion fuerte para documentos e imagenes con texto.
- Impacto: el OCR tendra dependencias pesadas, pero sera pieza central del pipeline.
- Alternativas consideradas: `Tesseract`.

## Version de Python fijada a `3.11`
- Fecha: 2026-03-12
- Estado: adoptada
- Area: entorno
- Decision: usar `Python 3.11` como version objetivo del proyecto.
- Motivo: `PaddleOCR` y `paddlepaddle` no funcionaron correctamente en el entorno inicial `Python 3.14`.
- Impacto: el proyecto debe instalarse con `Python >=3.11,<3.14` y el entorno virtual actual se recreo con `3.11`.
- Alternativas consideradas: mantener `3.14`, cambiar de OCR.

## OCR en Windows CPU con `MKLDNN` desactivado
- Fecha: 2026-03-12
- Estado: adoptada
- Area: OCR
- Decision: ejecutar `PaddleOCR` con `enable_mkldnn=False` y variables de entorno que desactivan `oneDNN/PIR`.
- Motivo: evita un fallo interno de inferencia en Windows CPU.
- Impacto: el OCR es estable en este entorno, aunque posiblemente algo menos optimizado.
- Alternativas consideradas: usar configuracion por defecto, cambiar de libreria OCR.

## Validaciones matematicas en codigo Python
- Fecha: 2026-03-12
- Estado: adoptada
- Area: reglas de negocio
- Decision: las sumas, subtotales, impuestos y consistencias se validan con codigo y no solo con el modelo.
- Motivo: es mas confiable y repetible que delegarlo completamente a una IA visual.
- Impacto: el sistema necesitara un motor de reglas claro y testeable.
- Alternativas consideradas: dejar validacion al modelo multimodal.

## `Ollama` como apoyo visual, no como unica fuente
- Fecha: 2026-03-12
- Estado: adoptada
- Area: arquitectura
- Decision: usar el modelo para detectar tachones, correcciones, sobrescrituras y alteraciones visuales, pero no como unica verdad para campos numericos.
- Motivo: los modelos visuales ayudan en lo visual, pero pueden fallar en precision numerica o en consistencia exacta.
- Impacto: el pipeline queda dividido entre OCR, analisis visual y reglas deterministicas.
- Alternativas consideradas: usar solo el modelo multimodal para todo el analisis.

## Entrada inicial por `image_url`
- Fecha: 2026-03-12
- Estado: adoptada
- Area: API
- Decision: el sistema comienza recibiendo imagenes por URL.
- Motivo: permite avanzar sin implementar scraping completo todavia.
- Impacto: se necesita una capa de descarga y validacion de imagenes remotas.
- Alternativas consideradas: subida manual de archivo, scraping desde el primer dia.

## Scraping diferido para una etapa posterior
- Fecha: 2026-03-12
- Estado: adoptada
- Area: roadmap
- Decision: no implementar scraping web en el MVP.
- Motivo: conviene estabilizar primero el pipeline de analisis antes de sumar otra fuente de complejidad.
- Impacto: el origen de imagenes debe quedar desacoplado del analisis.
- Alternativas consideradas: integrar scraping desde el inicio.

## Estructura modular por capas
- Fecha: 2026-03-12
- Estado: adoptada
- Area: arquitectura
- Decision: separar el proyecto en adquisicion de imagen, preprocesado, OCR, analisis visual, parsing, reglas y reporte.
- Motivo: facilita pruebas, mantenimiento y reemplazo de componentes.
- Impacto: la carpeta `app/services/` se organiza por responsabilidades.
- Alternativas consideradas: logica centralizada en pocos archivos.

## Documentacion viva en `documentos/`
- Fecha: 2026-03-12
- Estado: adoptada
- Area: proceso
- Decision: mantener en `documentos/` el plan, arquitectura, errores y decisiones tecnicas.
- Motivo: conservar memoria del proyecto y acelerar trabajo futuro.
- Impacto: cada paso importante deberia reflejarse en la documentacion correspondiente.
- Alternativas consideradas: no documentar o dejar notas dispersas.

## Pendientes de decision
- Definir si el proyecto tendra frontend propio al inicio o solo API.
- Definir formato exacto del JSON de salida final.
- Definir si se guardaran resultados en archivos o base de datos en el MVP.
- Definir conjunto inicial de documentos reales para prueba.
