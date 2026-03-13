from __future__ import annotations

from pathlib import Path
from typing import Callable
from uuid import uuid4

import pypdfium2 as pdfium
from PIL import Image, ImageOps

from app.services.performance_settings import OCR_IMAGE_MAX_SIDE_LIMIT, PDF_RENDER_SCALE

TEMP_DIR = Path("data/temp")
PageProgressCallback = Callable[[int, int, str], None]


def _resize_image_if_needed(
    image: Image.Image,
    *,
    max_side_limit: int = OCR_IMAGE_MAX_SIDE_LIMIT,
) -> tuple[Image.Image, dict[str, int | bool]]:
    original_width, original_height = image.size
    max_side = max(original_width, original_height)

    if max_side <= max_side_limit:
        return image, {
            "original_width": original_width,
            "original_height": original_height,
            "normalized_width": original_width,
            "normalized_height": original_height,
            "resized": False,
        }

    scale_factor = max_side_limit / max_side
    normalized_width = max(1, round(original_width * scale_factor))
    normalized_height = max(1, round(original_height * scale_factor))
    resized_image = image.resize(
        (normalized_width, normalized_height),
        Image.Resampling.LANCZOS,
    )

    return resized_image, {
        "original_width": original_width,
        "original_height": original_height,
        "normalized_width": normalized_width,
        "normalized_height": normalized_height,
        "resized": True,
    }


class DocumentNormalizationError(Exception):
    """Raised when a document cannot be normalized into page images."""


def _build_output_dir(file_stem: str) -> Path:
    output_dir = TEMP_DIR / f"{file_stem}_{uuid4().hex[:8]}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _build_output_path(output_dir: Path, page_number: int | None = None) -> Path:
    if page_number is None:
        return output_dir / "page_1.png"
    return output_dir / f"page_{page_number}.png"


def _normalize_image(
    file_path: str,
    *,
    progress_callback: PageProgressCallback | None = None,
) -> dict[str, object]:
    source_path = Path(file_path)
    output_dir = _build_output_dir(source_path.stem)

    try:
        with Image.open(file_path) as image:
            prepared_image = ImageOps.exif_transpose(image)
            normalized_image, dimensions = _resize_image_if_needed(prepared_image)

            output_path = _build_output_path(output_dir)
            normalized_image.save(output_path)
    except OSError as exc:
        raise DocumentNormalizationError("No se pudo preparar la imagen del documento.") from exc

    if progress_callback is not None:
        progress_callback(1, 1, "Normalizando pagina 1 de 1.")

    return {
        "page_count": 1,
        "pages": [
            {
                "page_number": 1,
                "image_path": str(output_path),
                **dimensions,
            }
        ],
    }


def _normalize_pdf(
    file_path: str,
    *,
    progress_callback: PageProgressCallback | None = None,
) -> dict[str, object]:
    pdf_path = Path(file_path)
    output_dir = _build_output_dir(pdf_path.stem)

    try:
        document = pdfium.PdfDocument(str(pdf_path))
    except Exception as exc:  # pragma: no cover - third-party wrapper
        raise DocumentNormalizationError("No se pudo abrir el PDF descargado.") from exc

    pages: list[dict[str, object]] = []
    try:
        total_pages = len(document)
        for page_index in range(total_pages):
            page = document.get_page(page_index)
            bitmap = page.render(scale=PDF_RENDER_SCALE)
            image = bitmap.to_pil()
            normalized_image, dimensions = _resize_image_if_needed(image)

            image_path = _build_output_path(output_dir, page_index + 1)
            normalized_image.save(image_path)

            pages.append(
                {
                    "page_number": page_index + 1,
                    "image_path": str(image_path),
                    **dimensions,
                }
            )
            if progress_callback is not None:
                progress_callback(
                    page_index + 1,
                    total_pages,
                    f"Normalizando pagina {page_index + 1} de {total_pages}.",
                )

            bitmap.close()
            page.close()
    except Exception as exc:  # pragma: no cover - third-party wrapper
        raise DocumentNormalizationError("No se pudo convertir el PDF a imagenes.") from exc
    finally:
        document.close()

    return {
        "page_count": len(pages),
        "pages": pages,
    }


def normalize_document(
    file_path: str,
    document_kind: str,
    *,
    progress_callback: PageProgressCallback | None = None,
) -> dict[str, object]:
    if document_kind == "image":
        return _normalize_image(file_path, progress_callback=progress_callback)
    if document_kind == "pdf":
        return _normalize_pdf(file_path, progress_callback=progress_callback)

    raise DocumentNormalizationError("Tipo de documento no soportado para normalizacion.")
