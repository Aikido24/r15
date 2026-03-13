from __future__ import annotations

from math import isclose


def evaluate_document_rules(parsed_fields: dict[str, object]) -> dict[str, object]:
    subtotal = parsed_fields.get("subtotal")
    tax = parsed_fields.get("tax")
    total = parsed_fields.get("total")
    missing_fields = list(parsed_fields.get("missing_fields", []))
    unclear_required_fields = list(parsed_fields.get("unclear_required_fields", []))

    checks: list[dict[str, object]] = []

    if subtotal is None or tax is None or total is None:
        checks.append(
            {
                "rule": "subtotal_plus_tax_equals_total",
                "passed": False,
                "message": "No se puede validar la suma porque faltan campos requeridos.",
            }
        )
    else:
        expected_total = float(subtotal) + float(tax)
        passed = isclose(expected_total, float(total), rel_tol=0.0, abs_tol=0.01)
        checks.append(
            {
                "rule": "subtotal_plus_tax_equals_total",
                "passed": passed,
                "message": (
                    "La suma es consistente."
                    if passed
                    else f"{subtotal:.2f} + {tax:.2f} no coincide con {total:.2f}."
                ),
            }
        )

    if missing_fields:
        checks.append(
            {
                "rule": "required_fields_present",
                "passed": False,
                "message": f"Faltan campos requeridos: {', '.join(missing_fields)}.",
            }
        )
    else:
        checks.append(
            {
                "rule": "required_fields_present",
                "passed": True,
                "message": "Los campos principales fueron detectados.",
            }
        )

    if unclear_required_fields:
        checks.append(
            {
                "rule": "required_fields_legible",
                "passed": False,
                "message": (
                    "Hay valores extraidos por vision con baja confianza o legibilidad insuficiente en: "
                    f"{', '.join(unclear_required_fields)}."
                ),
            }
        )
    else:
        checks.append(
            {
                "rule": "required_fields_legible",
                "passed": True,
                "message": "Los campos principales tienen legibilidad suficiente.",
            }
        )

    overall_ok = all(bool(check["passed"]) for check in checks)
    return {
        "overall_ok": overall_ok,
        "checks": checks,
    }
