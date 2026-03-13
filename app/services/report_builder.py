from __future__ import annotations


def _build_handwritten_message(
    *,
    page_number: int,
    value: str,
    region_description: str,
    confidence: str,
    legibility: str,
    reasoning: str,
) -> str:
    detected_value = value or "sin lectura confiable"
    region = region_description or "region no especificada"
    details = f"Pagina {page_number}: numero manuscrito '{detected_value}' en {region}."

    if legibility == "clear":
        details += f" Legibilidad clara, confianza {confidence}."
    elif legibility == "illegible":
        details += f" El numero es ilegible, confianza {confidence}."
    else:
        details += f" El numero es dudoso, confianza {confidence}."

    if reasoning:
        clean_reasoning = reasoning.rstrip(". ")
        details += f" Observacion: {clean_reasoning}."

    return details


def build_page_findings(page_visual_result: dict[str, object]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    page_number = int(page_visual_result["page_number"])

    if bool(page_visual_result.get("strikeouts_detected", False)):
        findings.append(
            {
                "type": "visual_strikeout",
                "severity": "high",
                "message": f"Pagina {page_number}: se detectaron posibles tachones.",
            }
        )

    if bool(page_visual_result.get("corrections_detected", False)):
        findings.append(
            {
                "type": "visual_correction",
                "severity": "high",
                "message": f"Pagina {page_number}: se detectaron posibles correcciones manuales.",
            }
        )

    if bool(page_visual_result.get("overwrites_detected", False)):
        findings.append(
            {
                "type": "visual_overwrite",
                "severity": "high",
                "message": f"Pagina {page_number}: se detectaron posibles sobrescrituras.",
            }
        )

    for area in list(page_visual_result.get("suspicious_areas", [])):
        findings.append(
            {
                "type": "visual_suspicious_area",
                "severity": "medium",
                "message": f"Pagina {page_number}: zona sospechosa detectada: {area}.",
            }
        )

    for handwritten_number in list(page_visual_result.get("handwritten_numbers", [])):
        value = str(handwritten_number.get("value", "")).strip()
        region_description = str(handwritten_number.get("region_description", "")).strip()
        confidence = str(handwritten_number.get("confidence", "low")).strip().lower()
        legibility = str(handwritten_number.get("legibility", "unclear")).strip().lower()
        reasoning = str(handwritten_number.get("reasoning", "")).strip()

        if legibility == "clear":
            finding_type = "handwritten_number_detected"
            severity = "medium"
        elif legibility == "illegible":
            finding_type = "handwritten_number_illegible"
            severity = "high"
        else:
            finding_type = "handwritten_number_unclear"
            severity = "high"

        findings.append(
            {
                "type": finding_type,
                "severity": severity,
                "message": _build_handwritten_message(
                    page_number=page_number,
                    value=value,
                    region_description=region_description,
                    confidence=confidence,
                    legibility=legibility,
                    reasoning=reasoning,
                ),
            }
        )

    return findings


def build_analysis_report(
    parsed_fields: dict[str, object],
    rule_results: dict[str, object],
    visual_result: dict[str, object],
    page_visual_results: list[dict[str, object]],
) -> dict[str, object]:
    findings: list[dict[str, str]] = []
    pages: list[dict[str, object]] = []

    for page_visual_result in page_visual_results:
        page_findings = build_page_findings(page_visual_result)
        pages.append(
            {
                "page_number": int(page_visual_result["page_number"]),
                "image_path": str(page_visual_result["image_path"]),
                "findings": page_findings,
            }
        )
        findings.extend(page_findings)

    for check in rule_results.get("checks", []):
        if not bool(check.get("passed", False)):
            findings.append(
                {
                    "type": "rule_validation",
                    "severity": "high",
                    "message": str(check.get("message", "")).strip(),
                }
            )

    missing_fields = list(parsed_fields.get("missing_fields", []))
    for field_name in missing_fields:
        findings.append(
            {
                "type": "missing_field",
                "severity": "medium",
                "message": f"No se detecto el campo {field_name}.",
            }
        )

    ok = not any(finding["severity"] == "high" for finding in findings)
    strikeout_count = sum(1 for finding in findings if finding["type"] == "visual_strikeout")
    handwritten_count = sum(
        1 for finding in findings if finding["type"].startswith("handwritten_number_")
    )

    if strikeout_count:
        summary = (
            f"Documento rechazado: se detectaron tachones en {strikeout_count} pagina(s)."
        )
    elif not findings:
        summary = "No se detectaron inconsistencias ni alteraciones visuales relevantes."
    else:
        summary = (
            f"Se detectaron {len(findings)} hallazgos en "
            f"{len(page_visual_results)} pagina(s) del documento."
        )
        if handwritten_count:
            summary += f" Se detectaron {handwritten_count} hallazgos relacionados con numeros manuscritos."

    return {
        "ok": ok,
        "summary": summary,
        "findings": findings,
        "pages": pages,
    }
