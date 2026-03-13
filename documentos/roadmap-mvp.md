# Roadmap del MVP

## Objetivo
Construir una primera version funcional del sistema que reciba una imagen por URL, extraiga texto, detecte alteraciones visuales basicas y valide sumas e inconsistencias.

## Resultado esperado del MVP
El MVP debe ser capaz de:
- recibir una `image_url`
- descargar la imagen
- ejecutar OCR
- extraer importes relevantes
- validar reglas matematicas simples
- consultar un modelo en `Ollama`
- devolver un JSON con hallazgos y resumen

## Criterios de exito
- La API responde correctamente a una imagen valida.
- El OCR devuelve texto util en documentos de prueba.
- El sistema detecta al menos inconsistencias matematicas simples.
- El modelo visual devuelve una respuesta estructurada.
- El resultado final combina OCR, reglas y analisis visual.

## Fase 1: Base del proyecto
### Objetivo
Dejar el proyecto listo para empezar a codificar.

### Tareas
- Confirmar estructura de carpetas.
- Confirmar `pyproject.toml`.
- Confirmar `.venv` y dependencias instaladas.
- Confirmar `Ollama` y modelo `qwen2.5vl:7b`.
- Crear archivos base del backend.

### Entregables
- Proyecto instalable y entorno listo.

## Fase 2: API minima
### Objetivo
Levantar una API funcional con endpoints basicos.

### Tareas
- Crear `app/main.py`.
- Crear rutas iniciales.
- Implementar `GET /health`.
- Implementar `POST /analyze` con respuesta simulada.
- Definir modelos de request y response.

### Entregables
- API arrancando localmente.
- Endpoint de salud funcionando.

## Fase 3: Descarga de imagen por URL
### Objetivo
Permitir que el backend obtenga una imagen remota de forma segura.

### Tareas
- Crear modulo para descarga de imagenes.
- Validar URL.
- Validar tipo de contenido.
- Validar tamano maximo.
- Guardar imagen temporal en `data/temp/`.

### Entregables
- Flujo de descarga estable desde `image_url`.

## Fase 4: OCR basico
### Objetivo
Extraer texto util desde la imagen descargada.

### Tareas
- Integrar `PaddleOCR`.
- Procesar imagenes de prueba.
- Devolver texto bruto y lineas detectadas.
- Guardar resultados de depuracion si hace falta.

### Entregables
- Servicio OCR funcional.

## Fase 5: Parsing de datos
### Objetivo
Transformar el texto OCR en datos mas utiles para validacion.

### Tareas
- Detectar importes.
- Detectar subtotal, impuestos y total cuando existan.
- Normalizar numeros.
- Marcar campos dudosos.

### Entregables
- Datos estructurados listos para reglas.

## Fase 6: Reglas matematicas
### Objetivo
Detectar inconsistencias numericas sin depender del modelo.

### Tareas
- Implementar regla `subtotal + impuesto = total`.
- Implementar suma de lineas cuando el documento lo permita.
- Detectar valores vacios o incoherentes.
- Preparar salida clara de errores de negocio.

### Entregables
- Motor de reglas minimo funcional.

## Fase 7: Analisis visual con Ollama
### Objetivo
Agregar deteccion visual basica de alteraciones.

### Tareas
- Crear servicio para consultar `Ollama`.
- Definir prompt fijo para:
  - tachones
  - correcciones
  - sobrescrituras
  - zonas sospechosas
- Forzar salida JSON.
- Manejar respuestas invalidas o incompletas.

### Entregables
- Analisis visual funcional con salida estructurada.

## Fase 8: Consolidacion del reporte
### Objetivo
Unir todos los resultados en una sola respuesta.

### Tareas
- Combinar OCR, parser, reglas y analisis visual.
- Crear estructura JSON final.
- Agregar resumen legible.
- Clasificar hallazgos por severidad.

### Entregables
- Endpoint `/analyze` con respuesta final real.

## Fase 9: Pruebas del MVP
### Objetivo
Validar que el MVP funciona con casos reales o semi reales.

### Tareas
- Reunir imagenes de prueba.
- Probar caso limpio.
- Probar caso con suma incorrecta.
- Probar caso con posible correccion visual.
- Registrar errores en `documentos/errores-y-soluciones.md`.

### Entregables
- Lista de resultados y fallos detectados.

## Fase 10: Ajustes posteriores al MVP
### Objetivo
Corregir los problemas mas visibles antes de ampliar alcance.

### Tareas
- Ajustar prompt del modelo.
- Mejorar parsing de importes.
- Mejorar manejo de errores.
- Agregar preprocesado de imagen si OCR falla.
- Refinar contrato de salida.

### Entregables
- MVP mas estable.

## Orden exacto recomendado
1. Crear `app/main.py`.
2. Crear `GET /health`.
3. Crear `POST /analyze` simulado.
4. Implementar descarga por URL.
5. Integrar OCR.
6. Parsear importes.
7. Implementar reglas matematicas.
8. Integrar `Ollama`.
9. Unir todo en respuesta final.
10. Probar con documentos reales.

## Archivos iniciales recomendados
- `app/main.py`
- `app/api/routes/analysis.py`
- `app/models/requests.py`
- `app/models/responses.py`
- `app/services/image_fetcher.py`
- `app/services/ocr_service.py`
- `app/services/parser_service.py`
- `app/services/rules_engine.py`
- `app/services/ollama_service.py`
- `app/services/report_builder.py`

## Riesgos del MVP
- OCR inestable con imagenes borrosas.
- Dificultad para identificar bien campos numericos.
- Respuestas no siempre consistentes del modelo visual.
- Diferencias grandes entre formatos de documentos.

## Regla de prioridad
Si hay conflicto entre lo que diga el modelo visual y lo que indiquen las reglas matematicas, para el MVP se debe priorizar:

1. validaciones deterministicas en Python
2. texto extraido por OCR
3. observaciones del modelo visual

## Checklist de cierre del MVP
- API funcional
- OCR funcional
- modelo visual operativo
- reglas matematicas operativas
- respuesta JSON consolidada
- pruebas minimas realizadas
- errores registrados
- decisiones actualizadas en documentacion
