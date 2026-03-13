from app.services.rules_engine import evaluate_document_rules
from app.services.vision_parser import parse_document_fields_from_visuals


def test_parse_document_fields_from_visuals_resolves_best_candidates() -> None:
    visual_result = {
        "detected_numbers": [
            {
                "page_number": 1,
                "value": "100",
                "field_name": "subtotal",
                "number_kind": "printed",
                "region_description": "fila subtotal",
                "confidence": "high",
                "legibility": "clear",
                "reasoning": "Coincide con la etiqueta subtotal.",
            },
            {
                "page_number": 1,
                "value": "19",
                "field_name": "tax",
                "number_kind": "printed",
                "region_description": "fila IVA",
                "confidence": "medium",
                "legibility": "clear",
                "reasoning": "Valor visible junto a IVA.",
            },
            {
                "page_number": 1,
                "value": "119",
                "field_name": "total",
                "number_kind": "handwritten",
                "region_description": "fila total",
                "confidence": "medium",
                "legibility": "unclear",
                "reasoning": "Se aprecia, pero el trazo no es perfecto.",
            },
        ]
    }

    parsed_fields = parse_document_fields_from_visuals(visual_result)

    assert parsed_fields["subtotal"] == 100.0
    assert parsed_fields["tax"] == 19.0
    assert parsed_fields["total"] == 119.0
    assert parsed_fields["missing_fields"] == []
    assert parsed_fields["unclear_required_fields"] == ["total"]
    assert parsed_fields["field_sources"]["total"]["number_kind"] == "handwritten"


def test_parse_document_fields_from_visuals_marks_missing_fields() -> None:
    parsed_fields = parse_document_fields_from_visuals({"detected_numbers": []})

    assert parsed_fields["subtotal"] is None
    assert parsed_fields["tax"] is None
    assert parsed_fields["total"] is None
    assert parsed_fields["missing_fields"] == ["subtotal", "tax", "total"]


def test_evaluate_document_rules_rejects_unclear_required_fields() -> None:
    rule_results = evaluate_document_rules(
        {
            "subtotal": 100.0,
            "tax": 19.0,
            "total": 119.0,
            "missing_fields": [],
            "unclear_required_fields": ["total"],
        }
    )

    failed_rules = [check["rule"] for check in rule_results["checks"] if not check["passed"]]
    assert "required_fields_legible" in failed_rules
