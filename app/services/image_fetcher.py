from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from typing import Callable

import httpx
from fastapi import UploadFile

TEMP_DIR = Path("data/temp")
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 64
SUPPORTED_CONTENT_TYPES = {"application/pdf"}
TransferProgressCallback = Callable[[int, int | None], None]


class DocumentDownloadError(Exception):
    """Raised when a remote document cannot be downloaded safely."""


def _guess_extension(content_type: str | None, url: str) -> str:
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed

    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix:
        return suffix

    return ".img"


def _get_document_kind(content_type: str) -> str:
    if content_type.startswith("image/"):
        return "image"
    if content_type in SUPPORTED_CONTENT_TYPES:
        return "pdf"
    raise DocumentDownloadError("La URL no apunta a una imagen ni a un PDF valido.")


def _build_document_result(
    *,
    file_name: str,
    file_path: Path,
    content_type: str,
    size_bytes: int,
    document_kind: str,
) -> dict[str, str | int]:
    return {
        "file_name": file_name,
        "file_path": str(file_path),
        "content_type": content_type,
        "size_bytes": size_bytes,
        "document_kind": document_kind,
    }


def download_document(
    document_url: str,
    *,
    progress_callback: TransferProgressCallback | None = None,
) -> dict[str, str | int]:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", document_url, follow_redirects=True, timeout=30.0) as response:
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        document_kind = _get_document_kind(content_type)
        total_expected = response.headers.get("content-length")
        total_expected_bytes = int(total_expected) if total_expected and total_expected.isdigit() else None

        extension = _guess_extension(content_type, document_url)
        file_name = f"{uuid4().hex}{extension}"
        file_path = TEMP_DIR / file_name

        total_bytes = 0
        with file_path.open("wb") as output_file:
            for chunk in response.iter_bytes(CHUNK_SIZE):
                if not chunk:
                    continue

                total_bytes += len(chunk)
                if total_bytes > MAX_DOCUMENT_BYTES:
                    output_file.close()
                    file_path.unlink(missing_ok=True)
                    raise DocumentDownloadError("El documento supera el tamano maximo permitido.")

                output_file.write(chunk)
                if progress_callback is not None:
                    progress_callback(total_bytes, total_expected_bytes)

    return _build_document_result(
        file_name=file_name,
        file_path=file_path,
        content_type=content_type,
        size_bytes=total_bytes,
        document_kind=document_kind,
    )


async def save_uploaded_document(
    upload: UploadFile,
    *,
    progress_callback: TransferProgressCallback | None = None,
) -> dict[str, str | int]:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    document_kind = _get_document_kind(content_type)
    total_expected_bytes = getattr(upload, "size", None)
    if total_expected_bytes is not None:
        total_expected_bytes = int(total_expected_bytes)

    original_name = upload.filename or f"upload{_guess_extension(content_type, '')}"
    extension = Path(original_name).suffix.lower() or _guess_extension(content_type, "")
    file_name = f"{uuid4().hex}{extension}"
    file_path = TEMP_DIR / file_name

    total_bytes = 0
    try:
        with file_path.open("wb") as output_file:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > MAX_DOCUMENT_BYTES:
                    output_file.close()
                    file_path.unlink(missing_ok=True)
                    raise DocumentDownloadError("El documento supera el tamano maximo permitido.")

                output_file.write(chunk)
                if progress_callback is not None:
                    progress_callback(total_bytes, total_expected_bytes)
    finally:
        await upload.close()

    return _build_document_result(
        file_name=original_name,
        file_path=file_path,
        content_type=content_type,
        size_bytes=total_bytes,
        document_kind=document_kind,
    )
