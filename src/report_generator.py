"""Clinical SOAP report generator grounded in sEMG biomarkers with guardrail validation."""

import json
import os
from pathlib import Path
import re

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from schemas.biomarkers_schema import SEMGAssessmentInput, SOAPReport
from src.numeric_guardrail import verify_soap_numbers

PROMPTS_DIR: Path = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_TEMPLATE_NAME: str = "soap_semg_v1.j2"
DEFAULT_LLM_MODEL: str = "gpt-4o-mini"

_CODE_FENCE_PATTERN: re.Pattern[str] = re.compile(
    r"^```(?:json)?\s*(.*?)\s*```$",
    re.DOTALL | re.IGNORECASE,
)


class _SOAPDraft(BaseModel):
    """Intermediate SOAP payload parsed prior to attaching guardrail audit results."""

    model_config = ConfigDict(str_strip_whitespace=True)

    patient_id: str = Field(..., min_length=1)
    subjective: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    assessment: str = Field(..., min_length=1)
    plan: str = Field(..., min_length=1)


def render_soap_prompt(
    assessment: SEMGAssessmentInput,
    template_name: str = DEFAULT_TEMPLATE_NAME,
    prompts_dir: Path = PROMPTS_DIR,
) -> str:
    """Render the Jinja2 clinical SOAP prompt template using assessment biomarkers."""
    env: Environment = Environment(
        loader=FileSystemLoader(str(prompts_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    return template.render(**assessment.model_dump())


def split_prompt_sections(rendered_prompt: str) -> tuple[str, str]:
    """Split a rendered SYSTEM/USER prompt template into separate message strings."""
    marker: str = "### USER"
    if marker not in rendered_prompt:
        return "", rendered_prompt.strip()

    system_part, user_part = rendered_prompt.split(marker, maxsplit=1)
    system_clean: str = re.sub(r"^###\s*SYSTEM\s*", "", system_part.strip(), count=1).strip()
    return system_clean, user_part.strip()


def format_soap_text(draft: _SOAPDraft) -> str:
    """Format a structured SOAP draft into canonical sectioned text for guardrail verification."""
    return (
        f"Subjective:\n{draft.subjective}\n\n"
        f"Objective:\n{draft.objective}\n\n"
        f"Assessment:\n{draft.assessment}\n\n"
        f"Plan:\n{draft.plan}"
    )


def _describe_symmetry(left_rms: float, right_rms: float, symmetry_pct: float) -> str:
    """Generate a clinical asymmetry statement without introducing arbitrary numeric thresholds."""
    if symmetry_pct >= 20.0:
        severity = "pronounced bilateral amplitude asymmetry"
    elif symmetry_pct >= 10.0:
        severity = "mild residual bilateral amplitude asymmetry"
    else:
        severity = "symmetric bilateral activation amplitude"

    if right_rms < left_rms:
        comparison = (
            f"reduced recruitment amplitude on the right side ({right_rms} uV) "
            f"relative to the left side ({left_rms} uV)"
        )
    elif left_rms < right_rms:
        comparison = (
            f"reduced recruitment amplitude on the left side ({left_rms} uV) "
            f"relative to the right side ({right_rms} uV)"
        )
    else:
        comparison = f"equal bilateral recruitment amplitude ({left_rms} uV bilaterally)"

    return (
        f"Bilateral sEMG amplitude analysis demonstrates {severity} "
        f"(Bilateral Symmetry Index {symmetry_pct}%), with {comparison}."
    )


def _describe_fatigue(
    left_mdf: float,
    right_mdf: float,
    left_slope: float,
    right_slope: float,
) -> str:
    """Generate a clinical spectral fatigue statement grounded in exact MDF and slope values."""
    steepest_slope: float = min(left_slope, right_slope)
    if steepest_slope <= -0.70:
        fatigue_profile = (
            "pronounced spectral compression consistent with progressive myoelectric fatigue"
        )
    elif steepest_slope <= -0.25:
        fatigue_profile = (
            "moderate negative spectral shift indicative of developing myoelectric fatigue"
        )
    else:
        fatigue_profile = (
            "minimal negative spectral shift consistent with preserved short-term endurance"
        )

    return (
        f"Frequency-domain analysis reveals {fatigue_profile}, with median frequency "
        f"values of {left_mdf} Hz (left) and {right_mdf} Hz (right) and fatigue slopes "
        f"of {left_slope} Hz/s (left) and {right_slope} Hz/s (right)."
    )


def _build_mock_draft(
    assessment: SEMGAssessmentInput,
    inject_hallucination: bool = False,
) -> _SOAPDraft:
    """Produce a deterministic clinical SOAP draft grounded in sEMG biomarkers.

    When ``inject_hallucination`` is True, intentionally alters the right-channel
    RMS amplitude and the bilateral symmetry index to simulate an LLM numeric
    hallucination for guardrail demonstration.
    """
    left = assessment.left_channel
    right = assessment.right_channel

    left_rms: float = left.rms_uv
    right_rms: float = (
        round(right.rms_uv + 25.0, 1) if inject_hallucination else right.rms_uv
    )
    symmetry_pct: float = (
        round(assessment.bilateral_symmetry_index_pct + 15.0, 1)
        if inject_hallucination
        else assessment.bilateral_symmetry_index_pct
    )

    subjective: str = (
        f"Clinical context for patient {assessment.patient_id}: "
        f"{assessment.clinical_context} "
        "No additional patient-reported symptoms were documented."
    )

    objective: str = (
        f"Muscle group evaluated: {assessment.muscle_group}. "
        f"Dominant side: {assessment.dominant_side}. "
        f"Left channel sEMG: RMS {left_rms} uV, MDF {left.mdf_hz} Hz, "
        f"MNF {left.mnf_hz} Hz, Fatigue Slope {left.fatigue_slope_hz_s} Hz/s. "
        f"Right channel sEMG: RMS {right_rms} uV, MDF {right.mdf_hz} Hz, "
        f"MNF {right.mnf_hz} Hz, Fatigue Slope {right.fatigue_slope_hz_s} Hz/s. "
        f"Bilateral Symmetry Index: {symmetry_pct}%."
    )

    assessment_section: str = (
        f"{_describe_symmetry(left_rms, right_rms, symmetry_pct)} "
        f"{_describe_fatigue(left.mdf_hz, right.mdf_hz, left.fatigue_slope_hz_s, right.fatigue_slope_hz_s)} "
        "Interpretation is strictly limited to the recorded sEMG biomarkers and "
        "documented clinical context."
    )

    plan: str = (
        f"Correlate objective sEMG findings for the {assessment.muscle_group} with "
        "clinical physical examination by the supervising clinician. "
        "Perform serial follow-up sEMG reassessment under an identical testing protocol "
        "to monitor bilateral activation symmetry and myoelectric fatigue progression. "
        "Guide non-pharmacological rehabilitation or ergonomic load adjustments based on "
        "longitudinal neuromuscular response."
    )

    return _SOAPDraft(
        patient_id=assessment.patient_id,
        subjective=subjective,
        objective=objective,
        assessment=assessment_section,
        plan=plan,
    )


def _parse_llm_json(raw_content: str, fallback_patient_id: str) -> _SOAPDraft:
    """Parse raw LLM completion content into a validated ``_SOAPDraft`` instance."""
    cleaned: str = raw_content.strip()
    fence_match: re.Match[str] | None = _CODE_FENCE_PATTERN.match(cleaned)
    if fence_match is not None:
        cleaned = fence_match.group(1).strip()

    payload: dict[str, object] = json.loads(cleaned)
    if not payload.get("patient_id"):
        payload["patient_id"] = fallback_patient_id
    return _SOAPDraft.model_validate(payload)


def _call_openai_api(
    messages: list[dict[str, str]],
    model: str,
    api_key: str,
    base_url: str | None = None,
) -> str:
    """Call an OpenAI-compatible chat completions endpoint and return message content."""
    client: OpenAI = (
        OpenAI(api_key=api_key, base_url=base_url)
        if base_url
        else OpenAI(api_key=api_key)
    )
    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=messages,
    )
    content: str | None = response.choices[0].message.content
    if not content:
        raise ValueError("LLM API returned an empty response payload.")
    return content


def _build_corrective_feedback(
    assessment: SEMGAssessmentInput,
    violations: list[str],
) -> str:
    """Build deterministic corrective feedback for a single guarded regeneration retry."""
    violation_lines: str = "\n".join(f"- {note}" for note in violations)
    return (
        "Your previous SOAP draft failed deterministic numeric verification with the "
        "following violations:\n"
        f"{violation_lines}\n\n"
        "Regenerate the complete JSON SOAP note strictly grounded in the exact input JSON "
        "biomarkers without altering, rounding, or inventing any numbers, medications, or "
        "diagnoses. Ensure the Objective section includes exact values for Left RMS "
        f"({assessment.left_channel.rms_uv} uV), Right RMS "
        f"({assessment.right_channel.rms_uv} uV), and Bilateral Symmetry Index "
        f"({assessment.bilateral_symmetry_index_pct}%)."
    )


def _finalize_report(
    assessment: SEMGAssessmentInput,
    draft: _SOAPDraft,
    guardrail_passed: bool,
    guardrail_notes: list[str],
) -> SOAPReport:
    """Construct the final Pydantic ``SOAPReport`` from a SOAP draft and audit outcome."""
    return SOAPReport(
        patient_id=assessment.patient_id,
        subjective=draft.subjective,
        objective=draft.objective,
        assessment=draft.assessment,
        plan=draft.plan,
        guardrail_passed=guardrail_passed,
        guardrail_notes=guardrail_notes,
    )


def generate_soap_report(
    assessment: SEMGAssessmentInput,
    mock: bool = True,
    inject_hallucination: bool = False,
) -> SOAPReport:
    """Generate and numerically verify a structured clinical SOAP report from sEMG biomarkers.

    Args:
        assessment: Validated bilateral sEMG biomarker assessment input.
        mock: When True, generates a deterministic clinical SOAP note without external
            API calls. When False, calls an OpenAI-compatible API configured via ``.env``.
        inject_hallucination: Only used when ``mock=True``. When True, intentionally
            corrupts one RMS value and the bilateral symmetry percentage on the first
            draft so the numeric guardrail rejects it and triggers a clean regeneration.

    Returns:
        Validated ``SOAPReport`` containing the clinical SOAP sections and guardrail
        audit status/notes.
    """
    rendered_prompt: str = render_soap_prompt(assessment)

    if mock:
        initial_draft: _SOAPDraft = _build_mock_draft(
            assessment,
            inject_hallucination=inject_hallucination,
        )
        initial_passed, initial_notes = verify_soap_numbers(
            assessment,
            format_soap_text(initial_draft),
        )
        if initial_passed:
            return _finalize_report(assessment, initial_draft, True, initial_notes)

        audit_notes: list[str] = [
            f"Initial draft rejected: {note}" for note in initial_notes
        ]
        clean_draft: _SOAPDraft = _build_mock_draft(
            assessment,
            inject_hallucination=False,
        )
        retry_passed, retry_notes = verify_soap_numbers(
            assessment,
            format_soap_text(clean_draft),
        )
        if retry_passed:
            audit_notes.append(
                "Clean regeneration pass succeeded: all sEMG biomarkers verified."
            )
            return _finalize_report(assessment, clean_draft, True, audit_notes)

        audit_notes.extend(f"Regeneration failed: {note}" for note in retry_notes)
        return _finalize_report(assessment, clean_draft, False, audit_notes)

    load_dotenv()
    api_key: str | None = os.getenv("LLM_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise ValueError(
            "Valid LLM_API_KEY must be configured in the environment or .env file "
            "when mock=False."
        )
    model: str = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
    base_url: str | None = os.getenv("LLM_BASE_URL")

    system_prompt, user_prompt = split_prompt_sections(rendered_prompt)
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    first_raw: str = _call_openai_api(
        messages=messages,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
    first_draft: _SOAPDraft = _parse_llm_json(first_raw, assessment.patient_id)
    first_passed, first_notes = verify_soap_numbers(
        assessment,
        format_soap_text(first_draft),
    )
    if first_passed:
        return _finalize_report(assessment, first_draft, True, first_notes)

    audit_notes = [f"Initial draft rejected: {note}" for note in first_notes]
    retry_messages: list[dict[str, str]] = [
        *messages,
        {"role": "assistant", "content": first_raw},
        {
            "role": "user",
            "content": _build_corrective_feedback(assessment, first_notes),
        },
    ]
    retry_raw: str = _call_openai_api(
        messages=retry_messages,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
    retry_draft: _SOAPDraft = _parse_llm_json(retry_raw, assessment.patient_id)
    retry_passed, retry_notes = verify_soap_numbers(
        assessment,
        format_soap_text(retry_draft),
    )
    if retry_passed:
        audit_notes.append(
            "Retry pass succeeded: all sEMG biomarkers verified."
        )
        return _finalize_report(assessment, retry_draft, True, audit_notes)

    audit_notes.extend(f"Retry failed: {note}" for note in retry_notes)
    return _finalize_report(assessment, retry_draft, False, audit_notes)
