from __future__ import annotations

from collections.abc import Callable
from threading import Thread

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.requests import AnalyzeRequest
from app.models.responses import AnalysisJobCreatedResponse, JobProgressResponse
from app.services.analysis_pipeline import (
    ProgressCallback,
    analyze_document_from_url,
    analyze_downloaded_document,
)
from app.services.document_normalizer import DocumentNormalizationError
from app.services.image_fetcher import DocumentDownloadError, save_uploaded_document
from app.services.ollama_service import OllamaAnalysisError
from app.services.progress_store import job_progress_store

router = APIRouter(tags=["analysis-jobs"])


def _build_create_response(job: JobProgressResponse) -> AnalysisJobCreatedResponse:
    return AnalysisJobCreatedResponse(
        job_id=job.job_id,
        status=job.status,
        stage=job.stage,
        progress_percent=job.progress_percent,
        message=job.message,
    )


def _describe_analysis_error(exc: Exception) -> str:
    if isinstance(exc, DocumentDownloadError):
        return str(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        return "No se pudo descargar el documento desde la URL proporcionada."
    if isinstance(exc, httpx.HTTPError):
        return "Error de red al intentar descargar el documento."
    if isinstance(exc, DocumentNormalizationError):
        return str(exc)
    if isinstance(exc, OllamaAnalysisError):
        return str(exc)
    return "Ocurrio un error inesperado durante el analisis."


def _job_progress_callback(job_id: str) -> ProgressCallback:
    def _callback(
        stage: str,
        progress_percent: int,
        message: str,
        current_page: int | None,
        total_pages: int | None,
    ) -> None:
        job_progress_store.update_job(
            job_id,
            status="running",
            stage=stage,
            progress_percent=progress_percent,
            message=message,
            current_page=current_page,
            total_pages=total_pages,
            error=None,
        )

    return _callback


def _run_url_job(job_id: str, source_url: str) -> None:
    try:
        result = analyze_document_from_url(
            source_url,
            progress_callback=_job_progress_callback(job_id),
        )
    except Exception as exc:
        job_progress_store.fail_job(
            job_id,
            error=_describe_analysis_error(exc),
            message="El analisis fallo.",
        )
        return

    job_progress_store.complete_job(
        job_id,
        result=result,
        message="Analisis completado.",
    )


def _run_file_job(job_id: str, download_result: dict[str, str | int]) -> None:
    try:
        result = analyze_downloaded_document(
            download_result,
            f"upload://{download_result['file_name']}",
            progress_callback=_job_progress_callback(job_id),
        )
    except Exception as exc:
        job_progress_store.fail_job(
            job_id,
            error=_describe_analysis_error(exc),
            message="El analisis fallo.",
        )
        return

    job_progress_store.complete_job(
        job_id,
        result=result,
        message="Analisis completado.",
    )


def _start_thread(target: Callable[..., None], *args: object) -> None:
    Thread(target=target, args=args, daemon=True).start()


@router.post("/analysis-jobs", response_model=AnalysisJobCreatedResponse)
def create_analysis_job(payload: AnalyzeRequest) -> AnalysisJobCreatedResponse:
    job = job_progress_store.create_job(
        status="queued",
        stage="queued",
        progress_percent=0,
        message="Trabajo en cola. Esperando inicio.",
    )
    _start_thread(_run_url_job, job.job_id, payload.source_url)
    return _build_create_response(job)


@router.post("/analysis-jobs/file", response_model=AnalysisJobCreatedResponse)
async def create_analysis_file_job(file: UploadFile = File(...)) -> AnalysisJobCreatedResponse:
    job = job_progress_store.create_job(
        status="queued",
        stage="queued",
        progress_percent=0,
        message="Trabajo en cola. Esperando carga del archivo.",
    )
    try:
        download_result = await save_uploaded_document(
            file,
            progress_callback=lambda bytes_written, total_bytes: job_progress_store.update_job(
                job.job_id,
                status="running",
                stage="saving_upload",
                progress_percent=0 if total_bytes is None else max(1, round((bytes_written / total_bytes) * 5)),
                message=(
                    "Guardando archivo subido."
                    if total_bytes is None
                    else f"Guardando archivo ({bytes_written} de {total_bytes} bytes)."
                ),
                error=None,
            ),
        )
    except DocumentDownloadError as exc:
        job_progress_store.fail_job(
            job.job_id,
            error=str(exc),
            message="No se pudo guardar el archivo enviado.",
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_progress_store.update_job(
        job.job_id,
        status="queued",
        stage="queued",
        progress_percent=5,
        message="Archivo recibido. Esperando inicio del analisis.",
        error=None,
    )
    _start_thread(_run_file_job, job.job_id, download_result)
    return _build_create_response(job_progress_store.get_job(job.job_id) or job)


@router.get("/analysis-jobs/{job_id}", response_model=JobProgressResponse)
def get_analysis_job(job_id: str) -> JobProgressResponse:
    job = job_progress_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No se encontro el job solicitado.")

    return job
