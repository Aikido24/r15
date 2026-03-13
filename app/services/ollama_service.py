from __future__ import annotations

import json
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from typing import Callable
from uuid import uuid4

import ollama
from PIL import Image, ImageOps

from app.services.performance_settings import (
    MAX_OLLAMA_WORKERS,
    OLLAMA_JPEG_QUALITY,
    OLLAMA_MAX_SIDE_LIMIT,
)
from app.models.responses import (
    DetectedFieldName,
    DetectedNumberKind,
    HandwrittenConfidence,
    HandwrittenLegibility,
)

OLLAMA_MODEL = "qwen2.5vl:7b"
OLLAMA_TEMP_DIR = Path("data/temp/ollama")
PageProgressCallback = Callable[[int, int, str], None]
logger = logging.getLogger(__name__)
VISUAL_ANALYSIS_PROMPT = """
Analiza esta imagen de documento y responde solo en JSON valido.

Objetivo:
1. Detectar si hay tachones visibles. Si existe cualquier tachon, debes reportarlo.
2. Detectar si hay correcciones manuales o sobrescrituras.
3. Detectar todos los numeros visibles relevantes en la pagina, tanto escritos a mano como impresos.
4. Clasificar cada numero como manuscrito, impreso o desconocido.
5. Indicar si cada numero es claro, dudoso o ilegible.
6. Marcar el campo al que parece pertenecer cada numero: subtotal, tax, total o other.
7. Detectar zonas sospechosas o alteraciones visuales en numeros o campos.

Responde exactamente con esta estructura:
{
  "strikeouts_detected": boolean,
  "corrections_detected": boolean,
  "overwrites_detected": boolean,
  "handwritten_numbers_detected": boolean,
  "detected_numbers": [
    {
      "value": "string",
      "field_name": "subtotal|tax|total|other",
      "number_kind": "handwritten|printed|unknown",
      "region_description": "string",
      "confidence": "high|medium|low",
      "legibility": "clear|unclear|illegible",
      "reasoning": "string"
    }
  ],
  "handwritten_numbers": [
    {
      "value": "string",
      "region_description": "string",
      "confidence": "high|medium|low",
      "legibility": "clear|unclear|illegible",
      "reasoning": "string"
    }
  ],
  "suspicious_areas": ["string"],
  "summary": "string"
}
""".strip()


class OllamaAnalysisError(Exception):
    """Raised when the visual analysis cannot be completed."""


def _normalize_field_name(value: object) -> DetectedFieldName:
    normalized_value = str(value).strip().lower()
    if normalized_value in {"subtotal", "tax", "total", "other"}:
        return normalized_value  # type: ignore[return-value]
    return "other"


def _normalize_number_kind(value: object) -> DetectedNumberKind:
    normalized_value = str(value).strip().lower()
    if normalized_value in {"handwritten", "printed", "unknown"}:
        return normalized_value  # type: ignore[return-value]
    return "unknown"


def _normalize_confidence(value: object) -> HandwrittenConfidence:
    normalized_value = str(value).strip().lower()
    if normalized_value in {"high", "medium", "low"}:
        return normalized_value  # type: ignore[return-value]
    return "low"


def _normalize_legibility(value: object) -> HandwrittenLegibility:
    normalized_value = str(value).strip().lower()
    if normalized_value in {"clear", "unclear", "illegible"}:
        return normalized_value  # type: ignore[return-value]
    return "unclear"


def _normalize_detected_numbers(
    value: object,
    *,
    page_number: int | None = None,
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    normalized_numbers: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        raw_detected_value = str(item.get("value", "")).strip()
        region_description = str(item.get("region_description", "")).strip()
        reasoning = str(item.get("reasoning", "")).strip()
        field_name = _normalize_field_name(item.get("field_name", "other"))
        number_kind = _normalize_number_kind(item.get("number_kind", "unknown"))
        confidence = _normalize_confidence(item.get("confidence", "low"))
        legibility = _normalize_legibility(item.get("legibility", "unclear"))

        if not any([raw_detected_value, region_description, reasoning]):
            continue

        normalized_numbers.append(
            {
                "page_number": page_number,
                "value": raw_detected_value,
                "field_name": field_name,
                "number_kind": number_kind,
                "region_description": region_description,
                "confidence": confidence,
                "legibility": legibility,
                "reasoning": reasoning,
            }
        )

    return normalized_numbers


def _normalize_handwritten_numbers(
    value: object,
    *,
    page_number: int | None = None,
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    normalized_numbers: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        raw_detected_value = str(item.get("value", "")).strip()
        region_description = str(item.get("region_description", "")).strip()
        reasoning = str(item.get("reasoning", "")).strip()
        confidence = _normalize_confidence(item.get("confidence", "low"))
        legibility = _normalize_legibility(item.get("legibility", "unclear"))

        if not any([raw_detected_value, region_description, reasoning]):
            continue

        normalized_numbers.append(
            {
                "page_number": page_number,
                "value": raw_detected_value,
                "region_description": region_description,
                "confidence": confidence,
                "legibility": legibility,
                "reasoning": reasoning,
            }
        )

    return normalized_numbers


def _prepare_image_for_ollama(image_path: str) -> str:
    source_path = Path(image_path)

    try:
        with Image.open(source_path) as image:
            prepared_image = ImageOps.exif_transpose(image)
            original_width, original_height = prepared_image.size
            max_side = max(original_width, original_height)

            if max_side <= OLLAMA_MAX_SIDE_LIMIT:
                return str(source_path)

            scale_factor = OLLAMA_MAX_SIDE_LIMIT / max_side
            resized_dimensions = (
                max(1, round(original_width * scale_factor)),
                max(1, round(original_height * scale_factor)),
            )
            resized_image = prepared_image.resize(resized_dimensions, Image.Resampling.LANCZOS)
            if resized_image.mode not in ("RGB", "L"):
                resized_image = resized_image.convert("RGB")

            OLLAMA_TEMP_DIR.mkdir(parents=True, exist_ok=True)
            output_path = OLLAMA_TEMP_DIR / f"{source_path.stem}_{uuid4().hex[:8]}.jpg"
            resized_image.save(
                output_path,
                format="JPEG",
                quality=OLLAMA_JPEG_QUALITY,
                optimize=True,
            )
            return str(output_path)
    except OSError as exc:
        raise OllamaAnalysisError("No se pudo preparar la imagen para el analisis visual.") from exc


def analyze_image_visuals(
    image_path: str,
    *,
    page_number: int | None = None,
) -> dict[str, object]:
    prepared_image_path = _prepare_image_for_ollama(image_path)
    started_at = perf_counter()

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": VISUAL_ANALYSIS_PROMPT,
                    "images": [prepared_image_path],
                }
            ],
            format="json",
            options={"temperature": 0},
        )
    except (ollama.RequestError, ollama.ResponseError) as exc:
        raise OllamaAnalysisError("No se pudo consultar el modelo local de Ollama.") from exc
    finally:
        if prepared_image_path != image_path:
            Path(prepared_image_path).unlink(missing_ok=True)

    try:
        content = json.loads(response.message.content)
    except json.JSONDecodeError as exc:
        raise OllamaAnalysisError("Ollama devolvio una respuesta no valida.") from exc

    suspicious_areas = content.get("suspicious_areas", [])
    if not isinstance(suspicious_areas, list):
        suspicious_areas = []
    detected_numbers = _normalize_detected_numbers(
        content.get("detected_numbers", []),
        page_number=page_number,
    )
    handwritten_numbers = _normalize_handwritten_numbers(
        content.get("handwritten_numbers", []),
        page_number=page_number,
    )
    handwritten_numbers_detected = bool(content.get("handwritten_numbers_detected", False))
    if not handwritten_numbers:
        handwritten_numbers = [
            {
                "page_number": number.get("page_number"),
                "value": str(number.get("value", "")).strip(),
                "region_description": str(number.get("region_description", "")).strip(),
                "confidence": number.get("confidence", "low"),
                "legibility": number.get("legibility", "unclear"),
                "reasoning": str(number.get("reasoning", "")).strip(),
            }
            for number in detected_numbers
            if str(number.get("number_kind", "unknown")) == "handwritten"
        ]
    if handwritten_numbers:
        handwritten_numbers_detected = True

    logger.info(
        "Visual page completed",
        extra={
            "page_number": page_number,
            "elapsed_ms": round((perf_counter() - started_at) * 1000),
        },
    )

    return {
        "strikeouts_detected": bool(content.get("strikeouts_detected", False)),
        "corrections_detected": bool(content.get("corrections_detected", False)),
        "overwrites_detected": bool(content.get("overwrites_detected", False)),
        "handwritten_numbers_detected": handwritten_numbers_detected,
        "detected_numbers": detected_numbers,
        "handwritten_numbers": handwritten_numbers,
        "suspicious_areas": [str(item) for item in suspicious_areas if str(item).strip()],
        "summary": str(content.get("summary", "")).strip(),
    }


def analyze_pages_visuals(
    pages: list[dict[str, object]],
    *,
    progress_callback: PageProgressCallback | None = None,
) -> dict[str, object]:
    started_at = perf_counter()
    page_results: list[dict[str, object]] = []
    suspicious_areas: list[str] = []
    strikeouts_detected = False
    corrections_detected = False
    overwrites_detected = False
    detected_numbers: list[dict[str, object]] = []
    handwritten_numbers: list[dict[str, object]] = []
    total_pages = len(pages)

    def _merge_page_result(page_number: int, image_path: str, page_visuals: dict[str, object]) -> None:
        nonlocal strikeouts_detected, corrections_detected, overwrites_detected

        strikeouts_detected = strikeouts_detected or bool(page_visuals["strikeouts_detected"])
        corrections_detected = corrections_detected or bool(page_visuals["corrections_detected"])
        overwrites_detected = overwrites_detected or bool(page_visuals["overwrites_detected"])
        detected_numbers.extend(list(page_visuals.get("detected_numbers", [])))
        handwritten_numbers.extend(list(page_visuals.get("handwritten_numbers", [])))

        page_suspicious_areas = [
            f"Pagina {page_number}: {area}"
            for area in list(page_visuals["suspicious_areas"])
        ]
        suspicious_areas.extend(page_suspicious_areas)
        page_results.append(
            {
                "page_number": page_number,
                "image_path": image_path,
                **page_visuals,
            }
        )

    if MAX_OLLAMA_WORKERS <= 1 or total_pages <= 1:
        for index, page in enumerate(pages, start=1):
            page_number = int(page["page_number"])
            image_path = str(page["image_path"])
            page_visuals = analyze_image_visuals(image_path, page_number=page_number)
            _merge_page_result(page_number, image_path, page_visuals)
            if progress_callback is not None:
                progress_callback(
                    index,
                    total_pages,
                    f"Analizando visualmente la pagina {page_number} ({index} de {total_pages}).",
                )
    else:
        completed_pages = 0
        with ThreadPoolExecutor(max_workers=MAX_OLLAMA_WORKERS) as executor:
            future_to_page = {
                executor.submit(
                    analyze_image_visuals,
                    str(page["image_path"]),
                    page_number=int(page["page_number"]),
                ): page
                for page in pages
            }

            for future in as_completed(future_to_page):
                page = future_to_page[future]
                page_number = int(page["page_number"])
                image_path = str(page["image_path"])
                page_visuals = future.result()
                completed_pages += 1
                _merge_page_result(page_number, image_path, page_visuals)
                if progress_callback is not None:
                    progress_callback(
                        completed_pages,
                        total_pages,
                        f"Analisis visual completado para pagina {page_number} ({completed_pages} de {total_pages}).",
                    )

        page_results.sort(key=lambda page: int(page["page_number"]))

    suspicious_areas = []
    for page_result in page_results:
        page_number = int(page_result["page_number"])
        suspicious_areas.extend(
            [
                f"Pagina {page_number}: {area}"
                for area in list(page_result["suspicious_areas"])
            ]
        )

    if not page_results:
        summary = "No se analizaron paginas."
    elif not suspicious_areas and not any(
        [strikeouts_detected, corrections_detected, overwrites_detected]
    ):
        summary = "No se detectaron alteraciones visuales relevantes en las paginas analizadas."
    else:
        summary = f"Se detectaron posibles hallazgos visuales en {len(suspicious_areas)} zonas."

    logger.info(
        "Visual stage completed",
        extra={
            "page_count": total_pages,
            "elapsed_ms": round((perf_counter() - started_at) * 1000),
            "max_workers": MAX_OLLAMA_WORKERS,
        },
    )

    return {
        "strikeouts_detected": strikeouts_detected,
        "corrections_detected": corrections_detected,
        "overwrites_detected": overwrites_detected,
        "handwritten_numbers_detected": bool(handwritten_numbers),
        "detected_numbers": detected_numbers,
        "handwritten_numbers": handwritten_numbers,
        "suspicious_areas": suspicious_areas,
        "summary": summary,
        "pages": page_results,
    }
