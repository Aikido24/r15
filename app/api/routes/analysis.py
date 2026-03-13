import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.requests import AnalyzeRequest
from app.models.responses import AnalyzeResponse
from app.services.analysis_pipeline import (
    analyze_document_from_url,
    analyze_downloaded_document,
)
from app.services.document_normalizer import DocumentNormalizationError
from app.services.image_fetcher import DocumentDownloadError, save_uploaded_document
from app.services.ollama_service import OllamaAnalysisError

router = APIRouter(tags=["analysis"])


def _raise_analysis_exception(exc: Exception) -> None:
    if isinstance(exc, DocumentDownloadError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=400,
            detail="No se pudo descargar el documento desde la URL proporcionada.",
        ) from exc
    if isinstance(exc, httpx.HTTPError):
        raise HTTPException(
            status_code=502,
            detail="Error de red al intentar descargar el documento.",
        ) from exc
    if isinstance(exc, DocumentNormalizationError):
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if isinstance(exc, OllamaAnalysisError):
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    raise exc


def _safe_analyze_downloaded_document(
    download_result: dict[str, str | int],
    source_reference: str,
) -> AnalyzeResponse:
    try:
        return analyze_downloaded_document(download_result, source_reference)
    except Exception as exc:
        _raise_analysis_exception(exc)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_document(payload: AnalyzeRequest) -> AnalyzeResponse:
    try:
        return analyze_document_from_url(payload.source_url)
    except Exception as exc:
        _raise_analysis_exception(exc)


@router.post("/analyze-file", response_model=AnalyzeResponse)
async def analyze_uploaded_document(file: UploadFile = File(...)) -> AnalyzeResponse:
    try:
        download_result = await save_uploaded_document(file)
    except DocumentDownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    source_reference = f"upload://{download_result['file_name']}"
    return _safe_analyze_downloaded_document(download_result, source_reference)
