from __future__ import annotations

from collections.abc import Callable
import logging
from time import perf_counter

from app.models.responses import (
    AnalyzeResponse,
    FindingResponse,
    PageAnalysisResponse,
    PageDimensionsResponse,
    ParsedFieldsResponse,
    RuleCheckResponse,
    VisualChecksResponse,
)
from app.services.document_normalizer import normalize_document
from app.services.image_fetcher import download_document
from app.services.ollama_service import analyze_pages_visuals
from app.services.report_builder import build_analysis_report
from app.services.rules_engine import evaluate_document_rules
from app.services.vision_parser import parse_document_fields_from_visuals

logger = logging.getLogger(__name__)
ProgressCallback = Callable[
    [str, int, str, int | None, int | None],
    None,
]

DOWNLOAD_STAGE_RANGE = (5, 20)
NORMALIZATION_STAGE_RANGE = (20, 35)
READING_STAGE_RANGE = (35, 85)


def _emit_progress(
    progress_callback: ProgressCallback | None,
    *,
    stage: str,
    progress_percent: int,
    message: str,
    current_page: int | None = None,
    total_pages: int | None = None,
) -> None:
    if progress_callback is None:
        return

    progress_callback(
        stage,
        progress_percent,
        message,
        current_page,
        total_pages,
    )


def _scale_progress(
    start_percent: int,
    end_percent: int,
    current_step: int,
    total_steps: int,
) -> int:
    if total_steps <= 0:
        return end_percent

    completed_ratio = current_step / total_steps
    return round(start_percent + ((end_percent - start_percent) * completed_ratio))


def _log_stage_timing(stage: str, started_at: float, **extra: object) -> None:
    logger.info(
        "Analysis stage completed",
        extra={
            "stage": stage,
            "elapsed_ms": round((perf_counter() - started_at) * 1000),
            **extra,
        },
    )


def _build_analyze_response(
    *,
    download_result: dict[str, str | int],
    source_reference: str,
    normalized_document: dict[str, object],
    parsed_fields: dict[str, object],
    rule_results: dict[str, object],
    visual_result: dict[str, object],
    report: dict[str, object],
) -> AnalyzeResponse:
    visual_pages_by_number = {
        int(page["page_number"]): page for page in list(visual_result["pages"])
    }
    normalized_pages_by_number = {
        int(page["page_number"]): page for page in list(normalized_document["pages"])
    }
    report_pages_by_number = {
        int(page["page_number"]): page for page in list(report["pages"])
    }
    page_responses: list[PageAnalysisResponse] = []
    for page in list(normalized_document["pages"]):
        page_number = int(page["page_number"])
        visual_page = visual_pages_by_number.get(page_number, {})
        normalized_page = normalized_pages_by_number.get(page_number, {})
        report_page = report_pages_by_number.get(page_number, {})

        page_responses.append(
            PageAnalysisResponse(
                page_number=page_number,
                image_path=str(page["image_path"]),
                dimensions=PageDimensionsResponse(
                    original_width=int(normalized_page.get("original_width", 0)),
                    original_height=int(normalized_page.get("original_height", 0)),
                    normalized_width=int(normalized_page.get("normalized_width", 0)),
                    normalized_height=int(normalized_page.get("normalized_height", 0)),
                    resized=bool(normalized_page.get("resized", False)),
                ),
                visual_checks=(
                    VisualChecksResponse(
                        strikeouts_detected=bool(visual_page.get("strikeouts_detected", False)),
                        corrections_detected=bool(visual_page.get("corrections_detected", False)),
                        overwrites_detected=bool(visual_page.get("overwrites_detected", False)),
                        handwritten_numbers_detected=bool(
                            visual_page.get("handwritten_numbers_detected", False)
                        ),
                        handwritten_numbers=list(visual_page.get("handwritten_numbers", [])),
                        detected_numbers=list(visual_page.get("detected_numbers", [])),
                        suspicious_areas=list(visual_page.get("suspicious_areas", [])),
                        summary=str(visual_page.get("summary", "")),
                    )
                    if visual_page
                    else None
                ),
                findings=[
                    FindingResponse(**finding)
                    for finding in list(report_page.get("findings", []))
                ],
            )
        )

    return AnalyzeResponse(
        ok=bool(report["ok"]),
        message="Documento procesado visualmente por pagina con Ollama.",
        summary=str(report["summary"]),
        document_url=source_reference,
        image_url=source_reference,
        document_kind=str(download_result["document_kind"]),
        page_count=int(normalized_document["page_count"]),
        file_name=str(download_result["file_name"]),
        file_path=str(download_result["file_path"]),
        content_type=str(download_result["content_type"]),
        size_bytes=int(download_result["size_bytes"]),
        parsed_fields=ParsedFieldsResponse(**parsed_fields),
        rule_checks=[RuleCheckResponse(**check) for check in list(rule_results["checks"])],
        visual_checks=VisualChecksResponse(
            strikeouts_detected=bool(visual_result["strikeouts_detected"]),
            corrections_detected=bool(visual_result["corrections_detected"]),
            overwrites_detected=bool(visual_result["overwrites_detected"]),
            handwritten_numbers_detected=bool(visual_result["handwritten_numbers_detected"]),
            handwritten_numbers=list(visual_result["handwritten_numbers"]),
            detected_numbers=list(visual_result["detected_numbers"]),
            suspicious_areas=list(visual_result["suspicious_areas"]),
            summary=str(visual_result["summary"]),
        ),
        findings=[FindingResponse(**finding) for finding in list(report["findings"])],
        pages=page_responses,
    )


def analyze_downloaded_document(
    download_result: dict[str, str | int],
    source_reference: str,
    *,
    progress_callback: ProgressCallback | None = None,
) -> AnalyzeResponse:
    total_started_at = perf_counter()
    _emit_progress(
        progress_callback,
        stage="normalizing_pages",
        progress_percent=NORMALIZATION_STAGE_RANGE[0],
        message="Preparando paginas del documento.",
    )
    normalization_started_at = perf_counter()
    normalized_document = normalize_document(
        str(download_result["file_path"]),
        str(download_result["document_kind"]),
        progress_callback=lambda current_page, total_pages, message: _emit_progress(
            progress_callback,
            stage="normalizing_pages",
            progress_percent=_scale_progress(
                NORMALIZATION_STAGE_RANGE[0],
                NORMALIZATION_STAGE_RANGE[1],
                current_page,
                total_pages,
            ),
            message=message,
            current_page=current_page,
            total_pages=total_pages,
        ),
    )
    _log_stage_timing(
        "normalizing_pages",
        normalization_started_at,
        page_count=int(normalized_document["page_count"]),
    )

    _emit_progress(
        progress_callback,
        stage="reading_document",
        progress_percent=READING_STAGE_RANGE[0],
        message="Iniciando lectura visual del documento con Ollama.",
        total_pages=int(normalized_document["page_count"]),
    )
    reading_started_at = perf_counter()
    visual_result = analyze_pages_visuals(
        list(normalized_document["pages"]),
        progress_callback=lambda current_page, total_pages, message: _emit_progress(
            progress_callback,
            stage="reading_document",
            progress_percent=_scale_progress(
                READING_STAGE_RANGE[0],
                READING_STAGE_RANGE[1],
                current_page,
                total_pages,
            ),
            message=message,
            current_page=current_page,
            total_pages=total_pages,
        ),
    )
    _log_stage_timing(
        "reading_document",
        reading_started_at,
        page_count=len(list(normalized_document["pages"])),
    )

    _emit_progress(
        progress_callback,
        stage="parsing_fields",
        progress_percent=62,
        message="Consolidando campos extraidos por vision.",
    )
    parsing_started_at = perf_counter()
    parsed_fields = parse_document_fields_from_visuals(visual_result)
    _log_stage_timing("parsing_fields", parsing_started_at)

    _emit_progress(
        progress_callback,
        stage="evaluating_rules",
        progress_percent=68,
        message="Validando reglas matematicas.",
    )
    rules_started_at = perf_counter()
    rule_results = evaluate_document_rules(parsed_fields)
    _log_stage_timing("evaluating_rules", rules_started_at)

    _emit_progress(
        progress_callback,
        stage="building_report",
        progress_percent=98,
        message="Consolidando reporte final.",
    )
    report_started_at = perf_counter()
    report = build_analysis_report(
        parsed_fields,
        rule_results,
        visual_result,
        list(visual_result["pages"]),
    )
    _log_stage_timing("building_report", report_started_at)

    response = _build_analyze_response(
        download_result=download_result,
        source_reference=source_reference,
        normalized_document=normalized_document,
        parsed_fields=parsed_fields,
        rule_results=rule_results,
        visual_result=visual_result,
        report=report,
    )
    _log_stage_timing(
        "analysis_total",
        total_started_at,
        page_count=int(normalized_document["page_count"]),
    )
    return response


def analyze_document_from_url(
    source_url: str,
    *,
    progress_callback: ProgressCallback | None = None,
) -> AnalyzeResponse:
    download_started_at = perf_counter()
    _emit_progress(
        progress_callback,
        stage="downloading_document",
        progress_percent=DOWNLOAD_STAGE_RANGE[0],
        message="Descargando documento desde la URL.",
    )
    download_result = download_document(
        source_url,
        progress_callback=lambda bytes_written, total_bytes: _emit_progress(
            progress_callback,
            stage="downloading_document",
            progress_percent=_scale_progress(
                DOWNLOAD_STAGE_RANGE[0],
                DOWNLOAD_STAGE_RANGE[1],
                bytes_written,
                total_bytes or bytes_written or 1,
            ),
            message=(
                "Descargando documento desde la URL."
                if total_bytes is None
                else f"Descargando documento ({bytes_written} de {total_bytes} bytes)."
            ),
        ),
    )
    _log_stage_timing("downloading_document", download_started_at)
    return analyze_downloaded_document(
        download_result,
        source_url,
        progress_callback=progress_callback,
    )
