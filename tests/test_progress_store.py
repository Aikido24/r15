from app.models.responses import AnalyzeResponse
from app.services.progress_store import JobProgressStore


def _build_result() -> AnalyzeResponse:
    return AnalyzeResponse(
        ok=True,
        message="Analisis completado.",
        document_url="upload://factura.pdf",
        image_url="upload://factura.pdf",
    )


def test_create_and_update_job_progress() -> None:
    store = JobProgressStore()

    created_job = store.create_job(
        job_id="job-1",
        message="Trabajo en cola.",
    )

    assert created_job.status == "queued"
    assert created_job.stage == "queued"
    assert created_job.progress_percent == 0
    assert created_job.result is None

    updated_job = store.update_job(
        "job-1",
        status="running",
        stage="running_ocr",
        progress_percent=135,
        message="Procesando pagina 2 de 4.",
        current_page=2,
        total_pages=4,
    )

    assert updated_job.status == "running"
    assert updated_job.stage == "running_ocr"
    assert updated_job.progress_percent == 100
    assert updated_job.current_page == 2
    assert updated_job.total_pages == 4
    assert updated_job.message == "Procesando pagina 2 de 4."


def test_complete_and_fail_job_replace_terminal_fields() -> None:
    store = JobProgressStore()
    store.create_job(job_id="job-2", status="running", stage="running_ocr")

    completed_job = store.complete_job("job-2", result=_build_result())

    assert completed_job.status == "completed"
    assert completed_job.stage == "completed"
    assert completed_job.progress_percent == 100
    assert completed_job.result is not None
    assert completed_job.error is None

    failed_job = store.fail_job("job-2", error="Ollama no responde.")

    assert failed_job.status == "failed"
    assert failed_job.stage == "failed"
    assert failed_job.result is None
    assert failed_job.error == "Ollama no responde."


def test_get_job_returns_copy() -> None:
    store = JobProgressStore()
    store.create_job(job_id="job-3")

    snapshot = store.get_job("job-3")

    assert snapshot is not None
    snapshot.message = "Mutacion externa"

    fresh_snapshot = store.get_job("job-3")
    assert fresh_snapshot is not None
    assert fresh_snapshot.message == ""
