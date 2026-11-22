"""Pydantic v2 data schemas for sEMG biomarker assessments and clinical SOAP reports."""

from pydantic import BaseModel, ConfigDict, Field


class ChannelMetrics(BaseModel):
    """Unilateral surface electromyography (sEMG) time- and frequency-domain metrics."""

    model_config = ConfigDict(str_strip_whitespace=True)

    rms_uv: float = Field(
        ...,
        ge=0.0,
        description="Root mean square (RMS) sEMG amplitude in microvolts (uV).",
    )
    mdf_hz: float = Field(
        ...,
        ge=0.0,
        description="Median frequency (MDF) of the sEMG power spectrum in hertz (Hz).",
    )
    mnf_hz: float = Field(
        ...,
        ge=0.0,
        description="Mean frequency (MNF) of the sEMG power spectrum in hertz (Hz).",
    )
    fatigue_slope_hz_s: float = Field(
        ...,
        description=(
            "Linear regression slope of median frequency over time in Hz/s; "
            "negative values indicate spectral compression associated with myoelectric fatigue."
        ),
    )


class SEMGAssessmentInput(BaseModel):
    """Structured bilateral sEMG assessment payload used as input for report generation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    patient_id: str = Field(
        ...,
        min_length=1,
        description="De-identified synthetic patient identifier.",
    )
    muscle_group: str = Field(
        ...,
        min_length=1,
        description="Anatomical muscle group evaluated during the sEMG protocol.",
    )
    clinical_context: str = Field(
        ...,
        min_length=1,
        description="Brief clinical background and testing protocol context.",
    )
    left_channel: ChannelMetrics = Field(
        ...,
        description="sEMG biomarker metrics recorded from the left-side channel.",
    )
    right_channel: ChannelMetrics = Field(
        ...,
        description="sEMG biomarker metrics recorded from the right-side channel.",
    )
    bilateral_symmetry_index_pct: float = Field(
        ...,
        ge=0.0,
        description=(
            "Bilateral amplitude asymmetry index expressed as a percentage (%); "
            "0% indicates complete bilateral symmetry."
        ),
    )
    dominant_side: str = Field(
        ...,
        min_length=1,
        description="Patient limb dominance (e.g., 'left', 'right').",
    )


class SOAPReport(BaseModel):
    """Structured clinical SOAP note generated from sEMG biomarkers with guardrail metadata."""

    model_config = ConfigDict(str_strip_whitespace=True)

    patient_id: str = Field(
        ...,
        min_length=1,
        description="De-identified patient identifier matching the input assessment.",
    )
    subjective: str = Field(
        ...,
        min_length=1,
        description="Subjective clinical context strictly derived from the input assessment.",
    )
    objective: str = Field(
        ...,
        min_length=1,
        description="Objective sEMG measurements reporting exact biomarker values and units.",
    )
    assessment: str = Field(
        ...,
        min_length=1,
        description="Clinical interpretation grounded strictly in the provided sEMG biomarkers.",
    )
    plan: str = Field(
        ...,
        min_length=1,
        description="Non-pharmacological clinical follow-up and monitoring recommendations.",
    )
    guardrail_passed: bool = Field(
        ...,
        description="Indicates whether the generated SOAP report passed all clinical guardrails.",
    )
    guardrail_notes: list[str] = Field(
        default_factory=list,
        description="Audit notes or violation messages produced during guardrail validation.",
    )
