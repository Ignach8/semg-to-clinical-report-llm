# semg-to-clinical-report-llm

## Overview and Clinical Motivation

`semg-to-clinical-report-llm` is a Python 3.11 clinical AI pipeline that translates quantitative surface electromyography (sEMG) biomarkers into structured clinical SOAP notes (Subjective, Objective, Assessment, Plan) with deterministic post-generation numeric verification.

Large language models can introduce subtle numerical errors—altering microvolt amplitudes, swapping bilateral channels, misstating spectral fatigue slopes, or omitting critical asymmetry metrics—when summarizing electrophysiological records. In clinical rehabilitation and occupational ergonomics documentation, numeric hallucination creates direct patient-safety and auditability risks. This repository addresses that failure mode by combining strict Pydantic v2 input/output schemas, grounded Jinja2 prompt templates, a regex-based deterministic numeric verification guardrail (`+/-0.1` rounding tolerance), and automated single-pass corrective regeneration before report export.

## Architecture and Workflow

```text
+-------------------+     +-----------------------+     +---------------------------+
|   sEMG Input JSON | --> |  Jinja2 Prompt        | --> |  LLM / Mock Generator     |
|  (Pydantic v2)    |     |  (soap_semg_v1.j2)    |     |  (Structured SOAP JSON)   |
+-------------------+     +-----------------------+     +-------------+-------------+
                                                                      |
                                                                      v
+-------------------+     +-----------------------+     +---------------------------+
| HTML & Markdown   | <-- |  Retry / Regenerate   | <-- |  Deterministic Numeric    |
| Clinical Reports  |     |  & Final Verification |     |  Guardrail (uV/Hz/Hz/s/%) |
+-------------------+     +-----------------------+     +---------------------------+
```

Core components:

- `schemas/biomarkers_schema.py`: Pydantic v2 models (`ChannelMetrics`, `SEMGAssessmentInput`, `SOAPReport`) enforcing strict types and non-negativity constraints on physical sEMG quantities.
- `prompts/soap_semg_v1.j2`: Clinical system/user Jinja2 prompt template prohibiting invented numbers, medications, or unsupported diagnoses and requiring verbatim reporting of RMS (`uV`), MDF (`Hz`), MNF (`Hz`), Fatigue Slope (`Hz/s`), and Bilateral Symmetry Index (`%`).
- `src/numeric_guardrail.py`: Deterministic verification engine (`verify_soap_numbers`) that extracts all clinical unit-bound numbers, verifies them against unit-indexed ground-truth sets within `+/-0.1` (`NUMERIC_HALLUCINATION`), and enforces presence of Left RMS, Right RMS, and Bilateral Symmetry Index in the Objective section (`MISSING_CRITICAL_METRIC`).
- `src/report_generator.py`: Orchestrates Jinja2 prompt rendering, deterministic mock generation (including optional hallucination injection for safety demonstration), OpenAI-compatible API execution (`--live`), guardrail validation, and single-retry corrective regeneration.
- `src/exporter.py`: Exports structured Markdown (`results/clinical_soap_reports.md`) and self-contained, print-ready clinical HTML (`results/clinical_soap_reports.html`) reports alongside serialized JSON (`results/soap_reports.json`).
- `main.py`: End-to-end CLI runner defaulting to deterministic mock mode, with `--live` for external OpenAI-compatible API execution.

## Quickstart

### 1. Environment Setup

```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2. Run the End-to-End Pipeline (Mock Mode)

Mock mode runs locally without external API credentials and intentionally injects a numeric hallucination into `PAT_001` on the first draft to demonstrate guardrail rejection and verified regeneration:

```bash
python main.py
```

To run against an OpenAI-compatible API instead, copy `.env.example` to `.env`, set `LLM_API_KEY` and `LLM_MODEL` (and optionally `LLM_BASE_URL`), then run:

```bash
python main.py --live
```

### 3. Run Unit Tests

```bash
pytest -v
```

### 4. View the Clinical HTML Report

Open `results/clinical_soap_reports.html` in any modern web browser:

- **Windows (PowerShell):** `Start-Process results\clinical_soap_reports.html`
- **macOS:** `open results/clinical_soap_reports.html`
- **Linux:** `xdg-open results/clinical_soap_reports.html`

## Sample Verification Results

Output summary table captured directly from `results/clinical_soap_reports.md` after running `python main.py`:

| Patient ID | Muscle Group | Symmetry Index (%) | Guardrail Status | Notes |
| :--- | :--- | ---: | :--- | :--- |
| PAT_001 | Quadriceps femoris (vastus lateralis) | 35.4% | PASS | Initial draft rejected (2 NUMERIC_HALLUCINATION, 2 MISSING_CRITICAL_METRIC); regenerated report verified. |
| PAT_002 | Quadriceps femoris (vastus lateralis) | 11.2% | PASS | All sEMG biomarkers verified on initial pass. |
| PAT_003 | Lumbar paraspinal (erector spinae, L4-L5) | 2.4% | PASS | All sEMG biomarkers verified on initial pass. |

## Synthetic Data Notice

All patient identifiers (`PAT_001`, `PAT_002`, `PAT_003`), clinical contexts, and sEMG biomarker measurements in `data/sample_biomarkers.json` are 100% synthetic and were authored solely for reproducible clinical AI safety testing. This repository contains no protected health information (PHI) or real clinical records and is not intended for direct clinical diagnosis or treatment decisions.
