from __future__ import annotations

import re

FIELD_NAMES = ("subtotal", "tax", "total")
CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}
LEGIBILITY_RANK = {"clear": 3, "unclear": 2, "illegible": 1}
AMOUNT_PATTERN = re.compile(r"[$€]?\s*\d[\d.,]*")


def _normalize_amount(raw_value: str) -> float | None:
    cleaned = re.sub(r"[^\d,.-]", "", raw_value.strip())
    if not cleaned:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) in {1, 2}:
            cleaned = ".".join(parts)
        else:
            cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_detected_amounts(detected_numbers: list[dict[str, object]]) -> list[float]:
    amounts: list[float] = []
    for number in detected_numbers:
        raw_value = str(number.get("value", "")).strip()
        if not raw_value:
            continue

        for match in AMOUNT_PATTERN.findall(raw_value):
            value = _normalize_amount(match)
            if value is not None:
                amounts.append(value)

    return amounts


def _candidate_rank(candidate: dict[str, object]) -> tuple[int, int]:
    return (
        CONFIDENCE_RANK.get(str(candidate.get("confidence", "low")).lower(), 1),
        LEGIBILITY_RANK.get(str(candidate.get("legibility", "unclear")).lower(), 1),
    )


def _resolve_field_candidate(
    detected_numbers: list[dict[str, object]],
    field_name: str,
) -> dict[str, object] | None:
    candidates = [
        number
        for number in detected_numbers
        if str(number.get("field_name", "other")).lower() == field_name
    ]
    if not candidates:
        return None

    ranked_candidates = sorted(candidates, key=_candidate_rank, reverse=True)
    return ranked_candidates[0]


def parse_document_fields_from_visuals(visual_result: dict[str, object]) -> dict[str, object]:
    detected_numbers = list(visual_result.get("detected_numbers", []))
    parsed_fields: dict[str, object] = {
        "detected_amounts": _extract_detected_amounts(detected_numbers),
        "missing_fields": [],
        "field_sources": {},
        "unclear_required_fields": [],
    }

    for field_name in FIELD_NAMES:
        candidate = _resolve_field_candidate(detected_numbers, field_name)
        if candidate is None:
            parsed_fields[field_name] = None
            parsed_fields["missing_fields"].append(field_name)
            continue

        raw_value = str(candidate.get("value", "")).strip()
        parsed_value = _normalize_amount(raw_value)
        legibility = str(candidate.get("legibility", "unclear")).lower()
        confidence = str(candidate.get("confidence", "low")).lower()

        parsed_fields[field_name] = parsed_value
        parsed_fields["field_sources"][field_name] = {
            "value": raw_value,
            "confidence": confidence,
            "legibility": legibility,
            "number_kind": str(candidate.get("number_kind", "unknown")).lower(),
            "region_description": str(candidate.get("region_description", "")).strip(),
        }

        if parsed_value is None:
            parsed_fields["missing_fields"].append(field_name)
            parsed_fields["unclear_required_fields"].append(field_name)
            continue

        if legibility != "clear" or confidence == "low":
            parsed_fields["unclear_required_fields"].append(field_name)

    return parsed_fields
