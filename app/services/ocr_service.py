from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from threading import local
from time import perf_counter
from typing import Callable

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")

from paddleocr import PaddleOCR

from app.services.performance_settings import MAX_OCR_WORKERS, OCR_TEXT_DET_LIMIT_SIDE_LEN

PageProgressCallback = Callable[[int, int, str], None]
logger = logging.getLogger(__name__)
_ocr_engine_local = local()


class OCRError(Exception):
    """Raised when OCR processing cannot be completed."""


@lru_cache(maxsize=1)
def get_ocr_engine() -> PaddleOCR:
    return _build_ocr_engine()


def _build_ocr_engine() -> PaddleOCR:
    return PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,
        text_det_limit_side_len=OCR_TEXT_DET_LIMIT_SIDE_LEN,
        text_det_limit_type="max",
    )


def _get_parallel_ocr_engine() -> PaddleOCR:
    engine = getattr(_ocr_engine_local, "engine", None)
    if engine is None:
        engine = _build_ocr_engine()
        _ocr_engine_local.engine = engine
    return engine


def extract_text(
    image_path: str,
    *,
    use_parallel_engine: bool = False,
    page_number: int | None = None,
) -> dict[str, str | list[str]]:
    started_at = perf_counter()
    try:
        ocr_engine = _get_parallel_ocr_engine() if use_parallel_engine else get_ocr_engine()
        results = ocr_engine.predict(image_path)
    except Exception as exc:  # pragma: no cover - wraps third-party errors
        raise OCRError("No se pudo ejecutar el OCR sobre la imagen.") from exc
    finally:
        elapsed_ms = round((perf_counter() - started_at) * 1000)
        logger.info(
            "OCR page completed",
            extra={
                "page_number": page_number,
                "elapsed_ms": elapsed_ms,
                "parallel_engine": use_parallel_engine,
            },
        )

    if not results:
        return {"raw_text": "", "detected_lines": []}

    first_page = results[0]
    detected_lines = [
        line.strip()
        for line in first_page.get("rec_texts", [])
        if isinstance(line, str) and line.strip()
    ]

    raw_text = "\n".join(detected_lines)
    return {
        "raw_text": raw_text,
        "detected_lines": detected_lines,
    }


def extract_text_from_pages(
    pages: list[dict[str, object]],
    *,
    progress_callback: PageProgressCallback | None = None,
) -> dict[str, object]:
    started_at = perf_counter()
    aggregated_lines: list[str] = []
    page_results: list[dict[str, object]] = []
    total_pages = len(pages)

    if MAX_OCR_WORKERS <= 1 or total_pages <= 1:
        for index, page in enumerate(pages, start=1):
            image_path = str(page["image_path"])
            page_number = int(page["page_number"])
            page_result = extract_text(image_path, page_number=page_number)
            page_lines = list(page_result["detected_lines"])

            aggregated_lines.extend(page_lines)
            page_results.append(
                {
                    "page_number": page_number,
                    "image_path": image_path,
                    "raw_text": str(page_result["raw_text"]),
                    "detected_lines": page_lines,
                }
            )
            if progress_callback is not None:
                progress_callback(
                    index,
                    total_pages,
                    f"Ejecutando OCR en pagina {page_number} ({index} de {total_pages}).",
                )
    else:
        completed_pages = 0
        with ThreadPoolExecutor(max_workers=MAX_OCR_WORKERS) as executor:
            future_to_page = {
                executor.submit(
                    extract_text,
                    str(page["image_path"]),
                    use_parallel_engine=True,
                    page_number=int(page["page_number"]),
                ): page
                for page in pages
            }

            for future in as_completed(future_to_page):
                page = future_to_page[future]
                image_path = str(page["image_path"])
                page_number = int(page["page_number"])
                page_result = future.result()
                page_lines = list(page_result["detected_lines"])
                completed_pages += 1

                page_results.append(
                    {
                        "page_number": page_number,
                        "image_path": image_path,
                        "raw_text": str(page_result["raw_text"]),
                        "detected_lines": page_lines,
                    }
                )
                if progress_callback is not None:
                    progress_callback(
                        completed_pages,
                        total_pages,
                        f"OCR completado para pagina {page_number} ({completed_pages} de {total_pages}).",
                    )

        page_results.sort(key=lambda page: int(page["page_number"]))
        for page in page_results:
            aggregated_lines.extend(list(page["detected_lines"]))

    logger.info(
        "OCR stage completed",
        extra={
            "page_count": total_pages,
            "elapsed_ms": round((perf_counter() - started_at) * 1000),
            "max_workers": MAX_OCR_WORKERS,
        },
    )

    return {
        "raw_text": "\n".join(aggregated_lines),
        "detected_lines": aggregated_lines,
        "pages": page_results,
    }
