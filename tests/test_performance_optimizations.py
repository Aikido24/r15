import time
from pathlib import Path

from PIL import Image

from app.services import analysis_pipeline, ocr_service, ollama_service
from app.services.document_normalizer import normalize_document
from app.services.performance_settings import OCR_IMAGE_MAX_SIDE_LIMIT
from app.services.report_builder import build_analysis_report, build_page_findings


def test_normalize_document_resizes_large_image_input(tmp_path: Path) -> None:
    image_path = tmp_path / "large-input.png"
    Image.new("RGB", (4000, 2000), color="white").save(image_path)

    normalized_document = normalize_document(str(image_path), "image")

    page = normalized_document["pages"][0]
    assert page["resized"] is True
    assert page["original_width"] == 4000
    assert page["normalized_width"] == OCR_IMAGE_MAX_SIDE_LIMIT
    assert page["normalized_height"] == 1000
    assert Path(str(page["image_path"])).exists()


def test_scale_progress_keeps_linear_progression() -> None:
    assert analysis_pipeline._scale_progress(35, 85, 1, 5) == 45
    assert analysis_pipeline._scale_progress(35, 85, 5, 5) == 85


def test_extract_text_from_pages_parallel_preserves_page_order(monkeypatch) -> None:
    pages = [
        {"page_number": 1, "image_path": "page-1.png"},
        {"page_number": 2, "image_path": "page-2.png"},
        {"page_number": 3, "image_path": "page-3.png"},
    ]
    progress_updates: list[tuple[int, int, str]] = []

    def fake_extract_text(
        image_path: str,
        *,
        use_parallel_engine: bool = False,
        page_number: int | None = None,
    ) -> dict[str, str | list[str]]:
        assert use_parallel_engine is True
        assert page_number is not None
        time.sleep(0.01 * (4 - page_number))
        return {
            "raw_text": f"text-{page_number}",
            "detected_lines": [f"line-{page_number}"],
        }

    monkeypatch.setattr(ocr_service, "MAX_OCR_WORKERS", 2)
    monkeypatch.setattr(ocr_service, "extract_text", fake_extract_text)

    ocr_result = ocr_service.extract_text_from_pages(
        pages,
        progress_callback=lambda current, total, message: progress_updates.append(
            (current, total, message)
        ),
    )

    assert [page["page_number"] for page in ocr_result["pages"]] == [1, 2, 3]
    assert ocr_result["detected_lines"] == ["line-1", "line-2", "line-3"]
    assert progress_updates[-1][0] == 3


def test_analyze_pages_visuals_parallel_preserves_page_order(monkeypatch) -> None:
    pages = [
        {"page_number": 1, "image_path": "page-1.png"},
        {"page_number": 2, "image_path": "page-2.png"},
        {"page_number": 3, "image_path": "page-3.png"},
    ]
    progress_updates: list[tuple[int, int, str]] = []

    def fake_analyze_image_visuals(
        image_path: str,
        *,
        page_number: int | None = None,
    ) -> dict[str, object]:
        assert page_number is not None
        time.sleep(0.01 * (4 - page_number))
        return {
            "strikeouts_detected": False,
            "corrections_detected": False,
            "overwrites_detected": False,
            "suspicious_areas": [f"area-{page_number}"],
            "summary": f"page-{page_number}",
        }

    monkeypatch.setattr(ollama_service, "MAX_OLLAMA_WORKERS", 2)
    monkeypatch.setattr(ollama_service, "analyze_image_visuals", fake_analyze_image_visuals)

    visual_result = ollama_service.analyze_pages_visuals(
        pages,
        progress_callback=lambda current, total, message: progress_updates.append(
            (current, total, message)
        ),
    )

    assert [page["page_number"] for page in visual_result["pages"]] == [1, 2, 3]
    assert visual_result["suspicious_areas"] == [
        "Pagina 1: area-1",
        "Pagina 2: area-2",
        "Pagina 3: area-3",
    ]
    assert progress_updates[-1][0] == 3


def test_build_page_findings_marks_unclear_handwritten_numbers_as_high() -> None:
    findings = build_page_findings(
        {
            "page_number": 2,
            "strikeouts_detected": False,
            "corrections_detected": False,
            "overwrites_detected": False,
            "suspicious_areas": [],
            "handwritten_numbers": [
                {
                    "value": "17",
                    "region_description": "conteo principal",
                    "confidence": "medium",
                    "legibility": "unclear",
                    "reasoning": "El trazo es tenue.",
                }
            ],
        }
    )

    assert findings == [
        {
            "type": "handwritten_number_unclear",
            "severity": "high",
            "message": "Pagina 2: numero manuscrito '17' en conteo principal. El numero es dudoso, confianza medium. Observacion: El trazo es tenue.",
        }
    ]


def test_build_analysis_report_rejects_strikeouts_and_summarizes_reason() -> None:
    report = build_analysis_report(
        parsed_fields={"missing_fields": []},
        rule_results={"checks": []},
        visual_result={},
        page_visual_results=[
            {
                "page_number": 1,
                "image_path": "page-1.png",
                "strikeouts_detected": True,
                "corrections_detected": False,
                "overwrites_detected": False,
                "suspicious_areas": [],
                "handwritten_numbers": [],
            }
        ],
    )

    assert report["ok"] is False
    assert report["summary"] == "Documento rechazado: se detectaron tachones en 1 pagina(s)."
    assert report["findings"][0]["type"] == "visual_strikeout"
