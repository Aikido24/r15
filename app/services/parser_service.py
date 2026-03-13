from __future__ import annotations

import re

FIELD_PATTERNS = {
    "subtotal": re.compile(r"\bsubtotal\b[\s:]*([$€]?\s*[\d.,]+)", re.IGNORECASE),
    "tax": re.compile(r"\b(?:iva|impuesto|tax)\b[\s:]*([$€]?\s*[\d.,]+)", re.IGNORECASE),
    "total": re.compile(r"(?<!sub)\btotal\b[\s:]*([$€]?\s*[\d.,]+)", re.IGNORECASE),
}
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


def _extract_field_value(field_name: str, text: str) -> float | None:
    pattern = FIELD_PATTERNS[field_name]
    match = pattern.search(text)
    if not match:
        return None

    return _normalize_amount(match.group(1))


def _extract_detected_amounts(lines: list[str]) -> list[float]:
    amounts: list[float] = []
    for line in lines:
        for match in AMOUNT_PATTERN.findall(line):
            value = _normalize_amount(match)
            if value is not None:
                amounts.append(value)
    return amounts


def parse_document_fields(raw_text: str, detected_lines: list[str]) -> dict[str, object]:
    subtotal = _extract_field_value("subtotal", raw_text)
    tax = _extract_field_value("tax", raw_text)
    total = _extract_field_value("total", raw_text)

    missing_fields = [
        field_name
        for field_name, value in {
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
        }.items()
        if value is None
    ]

    return {
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "detected_amounts": _extract_detected_amounts(detected_lines),
        "missing_fields": missing_fields,
    }
