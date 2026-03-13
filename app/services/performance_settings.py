from __future__ import annotations

import os


def _get_int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        value = default
    else:
        try:
            value = int(raw_value)
        except ValueError:
            value = default

    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)

    return value


def _get_float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        value = default
    else:
        try:
            value = float(raw_value)
        except ValueError:
            value = default

    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)

    return value


def _get_str(name: str, default: str, *, allowed: set[str] | None = None) -> str:
    value = os.getenv(name, default).strip() or default
    if allowed is not None and value not in allowed:
        return default
    return value


PDF_RENDER_SCALE = _get_float("PDF_RENDER_SCALE", 1.15, minimum=0.5, maximum=3.0)
OCR_IMAGE_MAX_SIDE_LIMIT = _get_int("OCR_IMAGE_MAX_SIDE_LIMIT", 2000, minimum=800)
OCR_TEXT_DET_LIMIT_SIDE_LEN = _get_int(
    "OCR_TEXT_DET_LIMIT_SIDE_LEN",
    OCR_IMAGE_MAX_SIDE_LIMIT,
    minimum=800,
)
OLLAMA_MAX_SIDE_LIMIT = _get_int("OLLAMA_MAX_SIDE_LIMIT", 1200, minimum=600)
OLLAMA_JPEG_QUALITY = _get_int("OLLAMA_JPEG_QUALITY", 78, minimum=40, maximum=95)
MAX_OCR_WORKERS = _get_int("MAX_OCR_WORKERS", 1, minimum=1, maximum=4)
MAX_OLLAMA_WORKERS = _get_int("MAX_OLLAMA_WORKERS", 1, minimum=1, maximum=2)
VISUAL_ANALYSIS_PAGE_LIMIT = _get_int("VISUAL_ANALYSIS_PAGE_LIMIT", 0, minimum=0)
VISUAL_ANALYSIS_SAMPLING_MODE = _get_str(
    "VISUAL_ANALYSIS_SAMPLING_MODE",
    "spread",
    allowed={"spread", "head"},
)
