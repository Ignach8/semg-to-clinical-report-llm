"""Deterministic numeric verification guardrail for sEMG-grounded clinical SOAP reports."""

from dataclasses import dataclass
import re

from schemas.biomarkers_schema import SEMGAssessmentInput

DEFAULT_TOLERANCE: float = 0.1
_FLOAT_EPSILON: float = 1e-9

_CLINICAL_NUMBER_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![A-Za-z0-9_.])"
    r"([+-]?\d+(?:\.\d+)?)"
    r"[ \t]*"
    r"(Hz/s(?![A-Za-z/])|Hz(?![A-Za-z])|[uµμ]V(?![A-Za-z])|%)",
    re.IGNORECASE,
)

_SECTION_HEADER_PATTERN: re.Pattern[str] = re.compile(
    r"(?im)"
    r"(?:^[ \t]*(?:#{1,6}[ \t]+)?(?:\*{1,2})?"
    r"(subjective|objective|assessment|plan)"
    r"(?:\*{1,2})?[ \t]*(?::[ \t]*(?:\*{1,2})?|$))"
    r"|"
    r"(?:\b(?:\*{1,2})?(subjective|objective|assessment|plan)(?:\*{1,2})?:[ \t]*)"
)


@dataclass(frozen=True)
class ExtractedMetric:
    """Numeric value and normalized clinical unit extracted from SOAP text."""

    value: float
    unit: str
    raw_text: str


def _normalize_text(text: str) -> str:
    """Normalize typographic minus signs to ASCII hyphens for reliable parsing."""
    return text.replace("\u2212", "-").replace("\u2013", "-")


def _normalize_unit(raw_unit: str) -> str:
    """Normalize clinical unit strings into canonical forms."""
    lowered: str = raw_unit.lower()
    if lowered == "hz/s":
        return "Hz/s"
    if lowered == "hz":
        return "Hz"
    if lowered in {"uv", "µv", "μv"}:
        return "uV"
    if lowered == "%":
        return "%"
    return raw_unit


def extract_clinical_numbers(text: str) -> list[ExtractedMetric]:
    """Extract all numeric values paired with supported clinical units from text."""
    normalized: str = _normalize_text(text)
    extracted: list[ExtractedMetric] = []
    for match in _CLINICAL_NUMBER_PATTERN.finditer(normalized):
        number_str: str = match.group(1)
        unit_str: str = _normalize_unit(match.group(2))
        extracted.append(
            ExtractedMetric(
                value=float(number_str),
                unit=unit_str,
                raw_text=match.group(0).strip(),
            )
        )
    return extracted


def build_allowed_values_by_unit(assessment: SEMGAssessmentInput) -> dict[str, set[float]]:
    """Build unit-indexed ground-truth numeric sets directly from an sEMG assessment."""
    left = assessment.left_channel
    right = assessment.right_channel
    return {
        "uV": {left.rms_uv, right.rms_uv},
        "Hz": {left.mdf_hz, left.mnf_hz, right.mdf_hz, right.mnf_hz},
        "Hz/s": {left.fatigue_slope_hz_s, right.fatigue_slope_hz_s},
        "%": {assessment.bilateral_symmetry_index_pct},
    }


def _extract_objective_section(soap_text: str) -> tuple[str, bool]:
    """Extract the Objective section body from SOAP text.

    Returns:
        A tuple of (section_text, has_soap_headers). When SOAP headers exist but
        no Objective header is present, returns ("", True). When no SOAP headers
        exist at all, falls back to (soap_text, False).
    """
    matches: list[re.Match[str]] = list(_SECTION_HEADER_PATTERN.finditer(soap_text))
    if not matches:
        return soap_text, False

    for index, match in enumerate(matches):
        section_name: str = (match.group(1) or match.group(2) or "").lower()
        if section_name == "objective":
            start: int = match.end()
            end: int = matches[index + 1].start() if index + 1 < len(matches) else len(soap_text)
            return soap_text[start:end], True

    return "", True


def _matches_value(value: float, expected: float, tolerance: float = DEFAULT_TOLERANCE) -> bool:
    """Return True if value is within the allowed rounding tolerance of expected."""
    return abs(value - expected) <= (tolerance + _FLOAT_EPSILON)


def _matches_any(
    value: float,
    allowed_values: set[float],
    tolerance: float = DEFAULT_TOLERANCE,
) -> bool:
    """Return True if value matches any ground-truth number within tolerance."""
    return any(_matches_value(value, target, tolerance) for target in allowed_values)


def verify_soap_numbers(
    assessment: SEMGAssessmentInput,
    soap_text: str,
) -> tuple[bool, list[str]]:
    """Verify clinical numbers in a SOAP note against ground-truth sEMG biomarkers.

    Checks performed:
    1. Flags any numeric value paired with clinical units (uV, Hz, Hz/s, %) in
       ``soap_text`` that does not match a ground-truth value in ``assessment``
       within +/-0.1 as ``NUMERIC_HALLUCINATION``.
    2. Verifies that critical biomarkers (Left RMS, Right RMS, and Bilateral
       Symmetry Index) appear in the Objective section, flagging omissions as
       ``MISSING_CRITICAL_METRIC``.

    Args:
        assessment: Ground-truth bilateral sEMG assessment input.
        soap_text: Full SOAP note text to validate.

    Returns:
        Tuple of ``(passed, notes)`` where ``passed`` is True only when no
        hallucinations or missing critical metrics are detected.
    """
    notes: list[str] = []
    allowed_by_unit: dict[str, set[float]] = build_allowed_values_by_unit(assessment)

    extracted_all: list[ExtractedMetric] = extract_clinical_numbers(soap_text)
    flagged_hallucinations: set[tuple[float, str]] = set()
    for metric in extracted_all:
        allowed_values: set[float] = allowed_by_unit.get(metric.unit, set())
        if not _matches_any(metric.value, allowed_values, DEFAULT_TOLERANCE):
            key: tuple[float, str] = (metric.value, metric.unit)
            if key in flagged_hallucinations:
                continue
            flagged_hallucinations.add(key)
            expected_sorted: list[float] = sorted(allowed_values)
            notes.append(
                f"NUMERIC_HALLUCINATION: Value '{metric.raw_text}' does not match "
                f"ground-truth {metric.unit} biomarkers {expected_sorted} "
                f"(tolerance +/-{DEFAULT_TOLERANCE})."
            )

    objective_text, has_soap_headers = _extract_objective_section(soap_text)
    if has_soap_headers and not objective_text.strip():
        notes.append(
            "MISSING_CRITICAL_METRIC: Objective section is missing from SOAP note."
        )

    objective_metrics: list[ExtractedMetric] = extract_clinical_numbers(objective_text)
    required_metrics: list[tuple[str, float, str]] = [
        ("Left RMS", assessment.left_channel.rms_uv, "uV"),
        ("Right RMS", assessment.right_channel.rms_uv, "uV"),
        ("Bilateral Symmetry Index", assessment.bilateral_symmetry_index_pct, "%"),
    ]

    for label, expected_value, expected_unit in required_metrics:
        present: bool = any(
            metric.unit == expected_unit
            and _matches_value(metric.value, expected_value, DEFAULT_TOLERANCE)
            for metric in objective_metrics
        )
        if not present:
            unit_suffix: str = "%" if expected_unit == "%" else f" {expected_unit}"
            notes.append(
                f"MISSING_CRITICAL_METRIC: {label} ({expected_value}{unit_suffix}) "
                f"was not found in the Objective section."
            )

    passed: bool = len(notes) == 0
    return passed, notes
