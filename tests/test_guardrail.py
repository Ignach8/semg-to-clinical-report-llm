"""Unit tests for numeric guardrail verification, SOAP recovery, and schema validation."""

from pydantic import ValidationError
import pytest

from schemas.biomarkers_schema import ChannelMetrics, SEMGAssessmentInput, SOAPReport
from src.numeric_guardrail import verify_soap_numbers
from src.report_generator import generate_soap_report


@pytest.fixture
def stroke_assessment() -> SEMGAssessmentInput:
    """Return a synthetic post-stroke quadriceps sEMG assessment matching PAT_001."""
    return SEMGAssessmentInput(
        patient_id="PAT_001",
        muscle_group="Quadriceps femoris (vastus lateralis)",
        clinical_context=(
            "Subacute post-stroke rehabilitation assessment during standardized "
            "isometric knee extension evaluating persistent right-sided weakness."
        ),
        left_channel=ChannelMetrics(
            rms_uv=123.6,
            mdf_hz=78.4,
            mnf_hz=91.2,
            fatigue_slope_hz_s=-0.32,
        ),
        right_channel=ChannelMetrics(
            rms_uv=86.4,
            mdf_hz=61.8,
            mnf_hz=73.5,
            fatigue_slope_hz_s=-0.74,
        ),
        bilateral_symmetry_index_pct=35.4,
        dominant_side="right",
    )


def test_verify_soap_numbers_passes_with_exact_biomarkers(
    stroke_assessment: SEMGAssessmentInput,
) -> None:
    """Guardrail passes with no audit notes when all reported numbers match ground truth."""
    soap_text: str = (
        "Subjective:\n"
        "Post-stroke quadriceps rehabilitation evaluation.\n\n"
        "Objective:\n"
        "Left channel: RMS 123.6 uV, MDF 78.4 Hz, MNF 91.2 Hz, Fatigue Slope -0.32 Hz/s. "
        "Right channel: RMS 86.4 uV, MDF 61.8 Hz, MNF 73.5 Hz, Fatigue Slope -0.74 Hz/s. "
        "Bilateral Symmetry Index: 35.4%.\n\n"
        "Assessment:\n"
        "Pronounced right-sided amplitude asymmetry (35.4%) with reduced right RMS (86.4 uV) "
        "versus left RMS (123.6 uV) and steeper right fatigue slope (-0.74 Hz/s).\n\n"
        "Plan:\n"
        "Serial sEMG reassessment under clinician supervision."
    )

    passed, notes = verify_soap_numbers(stroke_assessment, soap_text)

    assert passed is True
    assert notes == []


def test_verify_soap_numbers_flags_numeric_hallucination(
    stroke_assessment: SEMGAssessmentInput,
) -> None:
    """Guardrail catches altered RMS and symmetry values as NUMERIC_HALLUCINATION."""
    hallucinated_soap: str = (
        "Subjective:\n"
        "Post-stroke quadriceps rehabilitation evaluation.\n\n"
        "Objective:\n"
        "Left channel: RMS 150.0 uV, MDF 78.4 Hz, MNF 91.2 Hz, Fatigue Slope -0.32 Hz/s. "
        "Right channel: RMS 86.4 uV, MDF 61.8 Hz, MNF 73.5 Hz, Fatigue Slope -0.74 Hz/s. "
        "Bilateral Symmetry Index: 48.2%.\n\n"
        "Assessment:\n"
        "Right-sided quadriceps weakness with 48.2% asymmetry.\n\n"
        "Plan:\n"
        "Follow-up sEMG testing."
    )

    passed, notes = verify_soap_numbers(stroke_assessment, hallucinated_soap)

    assert passed is False
    hallucination_notes: list[str] = [
        note for note in notes if "NUMERIC_HALLUCINATION" in note
    ]
    assert any("150.0 uV" in note for note in hallucination_notes)
    assert any("48.2%" in note for note in hallucination_notes)


def test_verify_soap_numbers_flags_missing_critical_metrics(
    stroke_assessment: SEMGAssessmentInput,
) -> None:
    """Guardrail flags MISSING_CRITICAL_METRIC when required Objective metrics are omitted."""
    incomplete_soap: str = (
        "Subjective:\n"
        "Post-stroke quadriceps rehabilitation evaluation.\n\n"
        "Objective:\n"
        "Left channel: RMS 123.6 uV, MDF 78.4 Hz, Fatigue Slope -0.32 Hz/s.\n\n"
        "Assessment:\n"
        "Right-sided weakness observed with 86.4 uV on the right channel.\n\n"
        "Plan:\n"
        "Continue supervised rehabilitation."
    )

    passed, notes = verify_soap_numbers(stroke_assessment, incomplete_soap)

    assert passed is False
    missing_notes: list[str] = [
        note for note in notes if "MISSING_CRITICAL_METRIC" in note
    ]
    assert any("Right RMS" in note for note in missing_notes)
    assert any("Bilateral Symmetry Index" in note for note in missing_notes)


def test_verify_soap_numbers_respects_rounding_tolerance_and_unit_isolation(
    stroke_assessment: SEMGAssessmentInput,
) -> None:
    """Guardrail accepts +/-0.1 rounding variance but rejects cross-unit value swaps."""
    rounded_soap: str = (
        "Objective:\n"
        "Left RMS 123.7 uV, Right RMS 86.3 uV, MDF 78.5 Hz, "
        "Fatigue Slope -0.74 Hz/s, Bilateral Symmetry Index 35.5%."
    )
    passed_rounded, notes_rounded = verify_soap_numbers(stroke_assessment, rounded_soap)
    assert passed_rounded is True
    assert notes_rounded == []

    swapped_unit_soap: str = (
        "Objective:\n"
        "Left RMS 123.6 uV, Right RMS 86.4 uV, Bilateral Symmetry Index 86.4%."
    )
    passed_swapped, notes_swapped = verify_soap_numbers(stroke_assessment, swapped_unit_soap)
    assert passed_swapped is False
    assert any("NUMERIC_HALLUCINATION" in note and "86.4%" in note for note in notes_swapped)


def test_generate_soap_report_catches_injected_hallucination_and_recovers(
    stroke_assessment: SEMGAssessmentInput,
) -> None:
    """Mock pipeline catches injected numeric hallucinations and regenerates a verified report."""
    report: SOAPReport = generate_soap_report(
        stroke_assessment,
        mock=True,
        inject_hallucination=True,
    )

    assert isinstance(report, SOAPReport)
    assert report.patient_id == stroke_assessment.patient_id
    assert report.guardrail_passed is True
    assert any("NUMERIC_HALLUCINATION" in note for note in report.guardrail_notes)
    assert any("MISSING_CRITICAL_METRIC" in note for note in report.guardrail_notes)
    assert any("Clean regeneration pass succeeded" in note for note in report.guardrail_notes)
    assert "123.6 uV" in report.objective
    assert "86.4 uV" in report.objective
    assert "35.4%" in report.objective


def test_semg_assessment_input_rejects_malformed_payloads() -> None:
    """Pydantic schema validation rejects missing required fields and invalid field types."""
    with pytest.raises(ValidationError):
        SEMGAssessmentInput.model_validate(
            {
                "patient_id": "PAT_ERR_1",
                "muscle_group": "Quadriceps femoris",
                # Missing clinical_context, channels, symmetry index, and dominant_side
            }
        )

    with pytest.raises(ValidationError):
        SEMGAssessmentInput.model_validate(
            {
                "patient_id": "PAT_ERR_2",
                "muscle_group": "Quadriceps femoris",
                "clinical_context": "Synthetic validation test.",
                "left_channel": {
                    "rms_uv": "not_a_float",
                    "mdf_hz": 75.0,
                    "mnf_hz": 88.0,
                    "fatigue_slope_hz_s": -0.2,
                },
                "right_channel": {
                    "rms_uv": 90.0,
                    "mdf_hz": 72.0,
                    "mnf_hz": 85.0,
                    "fatigue_slope_hz_s": -0.3,
                },
                "bilateral_symmetry_index_pct": 12.0,
                "dominant_side": "right",
            }
        )

    with pytest.raises(ValidationError):
        SEMGAssessmentInput.model_validate(
            {
                "patient_id": "PAT_ERR_3",
                "muscle_group": "Quadriceps femoris",
                "clinical_context": "Negative RMS must fail non-negativity constraint.",
                "left_channel": {
                    "rms_uv": -15.0,
                    "mdf_hz": 75.0,
                    "mnf_hz": 88.0,
                    "fatigue_slope_hz_s": -0.2,
                },
                "right_channel": {
                    "rms_uv": 90.0,
                    "mdf_hz": 72.0,
                    "mnf_hz": 85.0,
                    "fatigue_slope_hz_s": -0.3,
                },
                "bilateral_symmetry_index_pct": 12.0,
                "dominant_side": "right",
            }
        )
