# Errores y soluciones

## Objetivo
Este documento sirve como memoria tecnica del proyecto para registrar errores, bloqueos, soluciones y decisiones operativas, y asi evitar repetir pasos o perder tiempo en problemas ya resueltos.

## Como usar este documento
- Registrar cada error relevante encontrado durante el desarrollo.
- Anotar la causa probable o confirmada.
- Guardar la solucion aplicada.
- Indicar si el problema quedo resuelto o si requiere seguimiento.
- Agregar fecha cuando sea util para llevar historial.

## Formato sugerido

```md
## [Titulo corto del problema]
- Fecha:
- Estado: resuelto | pendiente | monitorear
- Contexto:
- Sintoma:
- Causa:
- Solucion:
- Prevencion:
```

## Registro actual

## PowerShell no acepta `&&`
- Fecha: 2026-03-12
- Estado: resuelto
- Contexto: durante la instalacion del entorno en Windows.
- Sintoma: fallo al ejecutar varios comandos encadenados con `&&`.
- Causa: la sesion usada en PowerShell no acepto `&&` como separador en ese contexto.
- Solucion: usar `;` y el operador `&` para ejecutar binarios, por ejemplo `& ".\\.venv\\Scripts\\python.exe"`.
- Prevencion: en scripts de Windows para este proyecto, preferir sintaxis compatible con PowerShell.

## Falta de `README.md` al instalar con `pyproject.toml`
- Fecha: 2026-03-12
- Estado: resuelto
- Contexto: preparacion del entorno Python.
- Sintoma: riesgo de fallo porque `pyproject.toml` referencia `readme = "README.md"` y el archivo no existia.
- Causa: se definio metadata del proyecto antes de crear el archivo.
- Solucion: crear un `README.md` minimo antes de instalar el paquete editable.
- Prevencion: si `pyproject.toml` referencia archivos, crearlos antes de correr `pip install -e`.

## `ollama` no reconocido en PATH
- Fecha: 2026-03-12
- Estado: resuelto parcialmente
- Contexto: verificacion del runtime local de IA.
- Sintoma: el comando `ollama --version` fallaba aunque el programa ya estaba instalado.
- Causa: el ejecutable existia, pero la terminal actual no lo veia en el `PATH`.
- Solucion: usar la ruta completa `C:\\Users\\ju248\\AppData\\Local\\Programs\\Ollama\\ollama.exe`.
- Prevencion: abrir una terminal nueva despues de instalar `Ollama` o configurar el flujo usando la ruta completa mientras tanto.

## Descarga pesada del modelo multimodal
- Fecha: 2026-03-12
- Estado: resuelto
- Contexto: instalacion del modelo base para analisis visual.
- Sintoma: la descarga del modelo tardaba varios minutos y parecia no reflejarse de inmediato en `ollama list`.
- Causa: el modelo `qwen2.5vl:7b` pesa cerca de `6 GB` y la descarga/verificacion tarda bastante.
- Solucion: esperar a que finalice el proceso completo de `pull` y luego volver a consultar `ollama list`.
- Prevencion: contemplar tiempos largos de descarga para modelos multimodales y no asumir fallo antes de ver el cierre del proceso.

## Warning de dependencias en `requests`
- Fecha: 2026-03-12
- Estado: monitorear
- Contexto: verificacion de imports despues de instalar dependencias.
- Sintoma: aparecio `RequestsDependencyWarning` relacionado con versiones de `urllib3`, `chardet` o `charset_normalizer`.
- Causa: compatibilidad parcial entre versiones instaladas por dependencias transitivas.
- Solucion: no se aplico cambio inmediato porque no bloqueo la instalacion ni los imports.
- Prevencion: revisar este warning si aparecen fallos en OCR, descargas HTTP o integraciones que dependan de `requests`.

## `PaddleOCR` no funciona con `Python 3.14`
- Fecha: 2026-03-12
- Estado: resuelto
- Contexto: implementacion del OCR del MVP.
- Sintoma: `PaddleOCR` estaba instalado, pero fallaba con `ModuleNotFoundError: No module named 'paddle'`.
- Causa: `paddlepaddle` no tenia distribucion compatible para el entorno `Python 3.14` usado inicialmente.
- Solucion: instalar `Python 3.11`, recrear `.venv` con esa version e instalar `paddlepaddle`.
- Prevencion: fijar el proyecto a `Python >=3.11,<3.14` mientras `PaddleOCR` requiera ese rango.

## Error interno de `oneDNN/MKLDNN` en `PaddleOCR`
- Fecha: 2026-03-12
- Estado: resuelto
- Contexto: primera ejecucion real del OCR en Windows CPU.
- Sintoma: el OCR fallaba con `NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support ...` dentro de `oneDNN`.
- Causa: regression o incompatibilidad del backend `oneDNN/MKLDNN` de `paddlepaddle` en Windows CPU.
- Solucion: desactivar `MKLDNN/oneDNN` en el servicio OCR usando `enable_mkldnn=False` y variables de entorno `FLAGS_use_mkldnn=0` y `FLAGS_enable_pir_api=0`.
- Prevencion: mantener ese ajuste en el servicio OCR y revisar futuras versiones estables de `paddlepaddle`.

## Pendientes a vigilar
- Confirmar si en terminales nuevas `ollama` ya queda disponible sin ruta completa.
- Revisar el warning de `requests` si aparece comportamiento inesperado.
- Registrar aqui cualquier error de OCR, parsing de importes o respuestas invalidas del modelo.
