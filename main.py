"""End-to-end CLI pipeline for sEMG biomarker ingestion, SOAP generation, guardrail auditing, and export."""

import argparse
import json
from pathlib import Path
import sys

from pydantic import TypeAdapter

from schemas.biomarkers_schema import SEMGAssessmentInput, SOAPReport
from src.exporter import export_html_report, export_markdown_report
from src.report_generator import generate_soap_report

PROJECT_ROOT: Path = Path(__file__).resolve().parent
DATA_FILE: Path = PROJECT_ROOT / "data" / "sample_biomarkers.json"
RESULTS_DIR: Path = PROJECT_ROOT / "results"
JSON_OUTPUT: Path = RESULTS_DIR / "soap_reports.json"
MD_OUTPUT: Path = RESULTS_DIR / "clinical_soap_reports.md"
HTML_OUTPUT: Path = RESULTS_DIR / "clinical_soap_reports.html"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for pipeline execution mode."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=(
            "Generate deterministically verified clinical SOAP notes from "
            "surface electromyography (sEMG) biomarker assessments."
        )
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the configured OpenAI-compatible API instead of deterministic mock mode.",
    )
    return parser.parse_args(argv)


def load_assessments(data_path: Path = DATA_FILE) -> list[SEMGAssessmentInput]:
    """Load and validate sEMG biomarker assessments from JSON."""
    raw_text: str = data_path.read_text(encoding="utf-8")
    adapter: TypeAdapter[list[SEMGAssessmentInput]] = TypeAdapter(list[SEMGAssessmentInput])
    return adapter.validate_json(raw_text)


def export_json_reports(reports: list[SOAPReport], output_path: Path = JSON_OUTPUT) -> Path:
    """Serialize validated SOAPReport objects to formatted JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: list[dict[str, object]] = [report.model_dump() for report in reports]
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def _summarize_notes_for_table(report: SOAPReport) -> str:
    """Build a concise single-line verification summary for stdout table output."""
    if not report.guardrail_notes:
        return "Verified on initial pass (0 violations)"

    hallucinations: int = sum(
        1 for note in report.guardrail_notes if "NUMERIC_HALLUCINATION" in note
    )
    missing: int = sum(
        1 for note in report.guardrail_notes if "MISSING_CRITICAL_METRIC" in note
    )
    if report.guardrail_passed:
        return (
            f"Caught {hallucinations} hallucination(s), {missing} missing metric(s); "
            "regeneration verified"
        )
    return "; ".join(report.guardrail_notes)


def print_summary_table(
    assessments: list[SEMGAssessmentInput],
    reports: list[SOAPReport],
) -> None:
    """Print an aligned summary table of guardrail outcomes and detailed audit notes to stdout."""
    headers: list[str] = [
        "Patient ID",
        "Muscle Group",
        "Symmetry (%)",
        "Status",
        "Verification Notes",
    ]
    rows: list[list[str]] = []
    for assessment, report in zip(assessments, reports):
        status: str = "PASS" if report.guardrail_passed else "FAIL"
        rows.append(
            [
                assessment.patient_id,
                assessment.muscle_group,
                f"{assessment.bilateral_symmetry_index_pct:.1f}%",
                status,
                _summarize_notes_for_table(report),
            ]
        )

    col_widths: list[int] = [
        max(len(headers[col]), *(len(row[col]) for row in rows))
        for col in range(len(headers))
    ]

    header_line: str = " | ".join(
        headers[i].ljust(col_widths[i]) for i in range(len(headers))
    )
    separator_line: str = "-+-".join("-" * width for width in col_widths)

    print(header_line)
    print(separator_line)
    for row in rows:
        formatted_cells: list[str] = [
            row[0].ljust(col_widths[0]),
            row[1].ljust(col_widths[1]),
            row[2].rjust(col_widths[2]),
            row[3].ljust(col_widths[3]),
            row[4].ljust(col_widths[4]),
        ]
        print(" | ".join(formatted_cells))

    audited_reports: list[SOAPReport] = [r for r in reports if r.guardrail_notes]
    if audited_reports:
        print("\nDetailed Guardrail Audit Notes:")
        for report in audited_reports:
            print(f"  [{report.patient_id}]")
            for note in report.guardrail_notes:
                print(f"    - {note}")


def run_pipeline(live: bool = False) -> list[SOAPReport]:
    """Execute the end-to-end sEMG-to-SOAP generation, verification, and export pipeline."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    assessments: list[SEMGAssessmentInput] = load_assessments(DATA_FILE)
    mock_mode: bool = not live
    mode_label: str = "LIVE API" if live else "MOCK"

    print(f"sEMG-to-Clinical-Report Pipeline (Mode: {mode_label})")
    print(f"Loaded {len(assessments)} validated assessments from {DATA_FILE.relative_to(PROJECT_ROOT)}\n")

    reports: list[SOAPReport] = []
    for index, assessment in enumerate(assessments):
        inject_hallucination: bool = mock_mode and (
            index == 0 or assessment.patient_id == "PAT_001"
        )
        report: SOAPReport = generate_soap_report(
            assessment=assessment,
            mock=mock_mode,
            inject_hallucination=inject_hallucination,
        )
        reports.append(report)

    json_path: Path = export_json_reports(reports, JSON_OUTPUT)
    md_path: Path = export_markdown_report(assessments, reports, MD_OUTPUT)
    html_path: Path = export_html_report(assessments, reports, HTML_OUTPUT)

    print_summary_table(assessments, reports)
    print("\nExported Artifacts:")
    print(f"  - JSON:     {json_path.relative_to(PROJECT_ROOT)}")
    print(f"  - Markdown: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"  - HTML:     {html_path.relative_to(PROJECT_ROOT)}")
    return reports


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args: argparse.Namespace = parse_args(argv)
    reports: list[SOAPReport] = run_pipeline(live=args.live)
    return 0 if all(report.guardrail_passed for report in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
