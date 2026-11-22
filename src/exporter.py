"""Clinical Markdown and self-contained print-ready HTML report exporters."""

from datetime import datetime, timezone
from html import escape
from pathlib import Path

from schemas.biomarkers_schema import SEMGAssessmentInput, SOAPReport


def _validate_pairs(
    assessments: list[SEMGAssessmentInput],
    reports: list[SOAPReport],
) -> list[tuple[SEMGAssessmentInput, SOAPReport]]:
    """Validate one-to-one alignment between input assessments and generated SOAP reports."""
    if len(assessments) != len(reports):
        raise ValueError(
            f"Assessment count ({len(assessments)}) does not match report count ({len(reports)})."
        )
    pairs: list[tuple[SEMGAssessmentInput, SOAPReport]] = []
    for assessment, report in zip(assessments, reports):
        if assessment.patient_id != report.patient_id:
            raise ValueError(
                f"Mismatched patient_id pair: assessment '{assessment.patient_id}' "
                f"vs report '{report.patient_id}'."
            )
        pairs.append((assessment, report))
    return pairs


def _escape_md_cell(value: str) -> str:
    """Escape pipe characters and normalize line breaks for Markdown table cells."""
    return value.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").strip()


def _summarize_guardrail_notes(report: SOAPReport) -> str:
    """Create a concise single-line summary of guardrail verification notes."""
    if not report.guardrail_notes:
        return "All sEMG biomarkers verified on initial pass."

    hallucinations: int = sum(
        1 for note in report.guardrail_notes if "NUMERIC_HALLUCINATION" in note
    )
    missing: int = sum(
        1 for note in report.guardrail_notes if "MISSING_CRITICAL_METRIC" in note
    )

    if report.guardrail_passed:
        parts: list[str] = []
        if hallucinations:
            parts.append(f"{hallucinations} NUMERIC_HALLUCINATION")
        if missing:
            parts.append(f"{missing} MISSING_CRITICAL_METRIC")
        detail: str = ", ".join(parts) if parts else f"{len(report.guardrail_notes)} audit note(s)"
        return f"Initial draft rejected ({detail}); regenerated report verified."

    return "; ".join(report.guardrail_notes)


def export_markdown_report(
    assessments: list[SEMGAssessmentInput],
    reports: list[SOAPReport],
    output_path: str | Path = "results/clinical_soap_reports.md",
) -> Path:
    """Export sEMG assessments and verified SOAP notes to a structured Markdown report.

    Args:
        assessments: List of validated bilateral sEMG input assessments.
        reports: Corresponding list of generated SOAP reports.
        output_path: Destination file path for the Markdown output.

    Returns:
        Resolved Path to the written Markdown file.
    """
    pairs: list[tuple[SEMGAssessmentInput, SOAPReport]] = _validate_pairs(assessments, reports)
    destination: Path = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    timestamp: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "# Clinical sEMG SOAP Report Summary",
        "",
        f"Generated: {timestamp} | Total Assessments: {len(pairs)}",
        "",
        "## Guardrail Verification Summary",
        "",
        "| Patient ID | Muscle Group | Symmetry Index (%) | Guardrail Status | Notes |",
        "| :--- | :--- | ---: | :--- | :--- |",
    ]

    for assessment, report in pairs:
        status: str = "PASS" if report.guardrail_passed else "FAIL"
        summary_note: str = _summarize_guardrail_notes(report)
        lines.append(
            f"| {_escape_md_cell(assessment.patient_id)} "
            f"| {_escape_md_cell(assessment.muscle_group)} "
            f"| {assessment.bilateral_symmetry_index_pct:.1f}% "
            f"| {status} "
            f"| {_escape_md_cell(summary_note)} |"
        )

    lines.extend(["", "---", ""])

    for assessment, report in pairs:
        status = "PASS" if report.guardrail_passed else "FAIL"
        left = assessment.left_channel
        right = assessment.right_channel

        lines.extend(
            [
                f"## Patient {assessment.patient_id} - {assessment.muscle_group}",
                "",
                f"- **Dominant Side:** {assessment.dominant_side}",
                f"- **Bilateral Symmetry Index:** {assessment.bilateral_symmetry_index_pct:.1f}%",
                f"- **Guardrail Verification Status:** {status}",
                "",
                "### sEMG Biomarker Table",
                "",
                "| Biomarker | Left Channel | Right Channel | Units |",
                "| :--- | ---: | ---: | :--- |",
                f"| RMS Amplitude | {left.rms_uv} | {right.rms_uv} | uV |",
                f"| Median Frequency (MDF) | {left.mdf_hz} | {right.mdf_hz} | Hz |",
                f"| Mean Frequency (MNF) | {left.mnf_hz} | {right.mnf_hz} | Hz |",
                f"| Fatigue Slope | {left.fatigue_slope_hz_s} | {right.fatigue_slope_hz_s} | Hz/s |",
                f"| Bilateral Symmetry Index | {assessment.bilateral_symmetry_index_pct} | {assessment.bilateral_symmetry_index_pct} | % |",
                "",
                "### Structured SOAP Note",
                "",
                "**Subjective**",
                "",
                report.subjective,
                "",
                "**Objective**",
                "",
                report.objective,
                "",
                "**Assessment**",
                "",
                report.assessment,
                "",
                "**Plan**",
                "",
                report.plan,
                "",
                "### Guardrail Audit Trail",
                "",
            ]
        )

        if report.guardrail_notes:
            for note in report.guardrail_notes:
                lines.append(f"- {note}")
        else:
            lines.append("- Passed deterministic numeric verification on initial pass with zero violations.")

        lines.extend(["", "---", ""])

    destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return destination


def _build_html_styles() -> str:
    """Return self-contained medical typography and print-ready CSS styles."""
    return """
    :root {
      --bg-page: #f4f6f9;
      --bg-card: #ffffff;
      --bg-subtle: #f8fafc;
      --border-color: #d8e0ea;
      --text-primary: #142030;
      --text-secondary: #4a5b70;
      --accent-navy: #1b3a5c;
      --pass-bg: #e6f4ea;
      --pass-text: #137333;
      --pass-border: #a8dab5;
      --fail-bg: #fce8e6;
      --fail-text: #a50e0e;
      --fail-border: #f5b7b1;
    }

    *, *::before, *::after {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      padding: 2rem 1.25rem;
      background-color: var(--bg-page);
      color: var(--text-primary);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      font-size: 14px;
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
    }

    .container {
      max-width: 980px;
      margin: 0 auto;
    }

    .report-header {
      background-color: var(--accent-navy);
      color: #ffffff;
      padding: 1.5rem 1.75rem;
      border-radius: 8px;
      margin-bottom: 1.5rem;
    }

    .report-header h1 {
      margin: 0 0 0.35rem 0;
      font-size: 1.45rem;
      font-weight: 600;
      letter-spacing: -0.01em;
    }

    .report-meta {
      margin: 0;
      font-size: 0.875rem;
      color: #d7e3f1;
    }

    .section-card,
    .patient-card {
      background-color: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.5rem;
    }

    .section-title {
      margin: 0 0 0.85rem 0;
      font-size: 1.05rem;
      font-weight: 600;
      color: var(--accent-navy);
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 0.45rem;
    }

    .card-header {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: flex-start;
      gap: 0.75rem;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 0.85rem;
      margin-bottom: 1rem;
    }

    .card-header h2 {
      margin: 0 0 0.25rem 0;
      font-size: 1.15rem;
      color: var(--accent-navy);
    }

    .patient-subtitle {
      margin: 0;
      font-size: 0.875rem;
      color: var(--text-secondary);
    }

    .badge {
      display: inline-block;
      padding: 0.25rem 0.65rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      border: 1px solid transparent;
      white-space: nowrap;
    }

    .badge-pass {
      background-color: var(--pass-bg);
      color: var(--pass-text);
      border-color: var(--pass-border);
    }

    .badge-fail {
      background-color: var(--fail-bg);
      color: var(--fail-text);
      border-color: var(--fail-border);
    }

    .table-wrapper {
      overflow-x: auto;
      margin-bottom: 1rem;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
      font-variant-numeric: tabular-nums;
    }

    th, td {
      padding: 0.55rem 0.7rem;
      border: 1px solid var(--border-color);
      text-align: left;
      vertical-align: top;
    }

    thead th {
      background-color: var(--bg-subtle);
      color: var(--accent-navy);
      font-weight: 600;
    }

    th.num, td.num {
      text-align: right;
      white-space: nowrap;
    }

    .soap-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 0.75rem;
      margin-top: 0.5rem;
    }

    .soap-block {
      background-color: var(--bg-subtle);
      border: 1px solid var(--border-color);
      border-left: 3px solid var(--accent-navy);
      border-radius: 4px;
      padding: 0.75rem 0.95rem;
    }

    .soap-block h3 {
      margin: 0 0 0.3rem 0;
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--accent-navy);
    }

    .soap-block p {
      margin: 0;
      color: var(--text-primary);
    }

    .audit-box {
      margin-top: 1rem;
      padding: 0.75rem 0.95rem;
      border-radius: 4px;
      background-color: var(--bg-subtle);
      border: 1px solid var(--border-color);
    }

    .audit-box h3 {
      margin: 0 0 0.4rem 0;
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--text-secondary);
    }

    .audit-box ul {
      margin: 0;
      padding-left: 1.2rem;
      font-size: 0.85rem;
      color: var(--text-secondary);
    }

    .audit-box li {
      margin-bottom: 0.25rem;
    }

    .report-footer {
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-secondary);
      margin-top: 1rem;
    }

    @media print {
      @page {
        margin: 14mm;
      }

      body {
        background-color: #ffffff;
        padding: 0;
        font-size: 11pt;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }

      .container {
        max-width: none;
      }

      .patient-card,
      .section-card,
      .soap-block,
      .audit-box {
        break-inside: avoid;
      }
    }
    """.strip()


def export_html_report(
    assessments: list[SEMGAssessmentInput],
    reports: list[SOAPReport],
    output_path: str | Path = "results/clinical_soap_reports.html",
) -> Path:
    """Export sEMG assessments and verified SOAP notes to a self-contained clinical HTML report.

    Args:
        assessments: List of validated bilateral sEMG input assessments.
        reports: Corresponding list of generated SOAP reports.
        output_path: Destination file path for the HTML output.

    Returns:
        Resolved Path to the written HTML file.
    """
    pairs: list[tuple[SEMGAssessmentInput, SOAPReport]] = _validate_pairs(assessments, reports)
    destination: Path = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    timestamp: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    passed_count: int = sum(1 for _, report in pairs if report.guardrail_passed)

    summary_rows: list[str] = []
    for assessment, report in pairs:
        badge_class: str = "badge-pass" if report.guardrail_passed else "badge-fail"
        status_label: str = "PASS" if report.guardrail_passed else "FAIL"
        summary_note: str = _summarize_guardrail_notes(report)
        summary_rows.append(
            "<tr>"
            f"<td><strong>{escape(assessment.patient_id)}</strong></td>"
            f"<td>{escape(assessment.muscle_group)}</td>"
            f"<td class=\"num\">{assessment.bilateral_symmetry_index_pct:.1f}%</td>"
            f"<td><span class=\"badge {badge_class}\">{status_label}</span></td>"
            f"<td>{escape(summary_note)}</td>"
            "</tr>"
        )

    patient_cards: list[str] = []
    for assessment, report in pairs:
        left = assessment.left_channel
        right = assessment.right_channel
        badge_class = "badge-pass" if report.guardrail_passed else "badge-fail"
        status_label = "GUARDRAIL PASS" if report.guardrail_passed else "GUARDRAIL FAIL"

        if report.guardrail_notes:
            audit_items = "".join(
                f"<li>{escape(note)}</li>" for note in report.guardrail_notes
            )
        else:
            audit_items = (
                "<li>Passed deterministic numeric verification on initial pass with zero violations.</li>"
            )

        patient_cards.append(
            f"""
    <article class="patient-card">
      <div class="card-header">
        <div>
          <h2>Patient {escape(assessment.patient_id)} &mdash; {escape(assessment.muscle_group)}</h2>
          <p class="patient-subtitle">
            Dominant Side: {escape(assessment.dominant_side)} |
            Bilateral Symmetry Index: {assessment.bilateral_symmetry_index_pct:.1f}%
          </p>
        </div>
        <span class="badge {badge_class}">{status_label}</span>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th scope="col">sEMG Biomarker</th>
              <th scope="col" class="num">Left Channel</th>
              <th scope="col" class="num">Right Channel</th>
              <th scope="col">Units</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">RMS Amplitude</th>
              <td class="num">{left.rms_uv}</td>
              <td class="num">{right.rms_uv}</td>
              <td>uV</td>
            </tr>
            <tr>
              <th scope="row">Median Frequency (MDF)</th>
              <td class="num">{left.mdf_hz}</td>
              <td class="num">{right.mdf_hz}</td>
              <td>Hz</td>
            </tr>
            <tr>
              <th scope="row">Mean Frequency (MNF)</th>
              <td class="num">{left.mnf_hz}</td>
              <td class="num">{right.mnf_hz}</td>
              <td>Hz</td>
            </tr>
            <tr>
              <th scope="row">Fatigue Slope</th>
              <td class="num">{left.fatigue_slope_hz_s}</td>
              <td class="num">{right.fatigue_slope_hz_s}</td>
              <td>Hz/s</td>
            </tr>
            <tr>
              <th scope="row">Bilateral Symmetry Index</th>
              <td class="num" colspan="2">{assessment.bilateral_symmetry_index_pct:.1f}</td>
              <td>%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="soap-grid">
        <div class="soap-block">
          <h3>Subjective</h3>
          <p>{escape(report.subjective)}</p>
        </div>
        <div class="soap-block">
          <h3>Objective</h3>
          <p>{escape(report.objective)}</p>
        </div>
        <div class="soap-block">
          <h3>Assessment</h3>
          <p>{escape(report.assessment)}</p>
        </div>
        <div class="soap-block">
          <h3>Plan</h3>
          <p>{escape(report.plan)}</p>
        </div>
      </div>

      <div class="audit-box">
        <h3>Guardrail Audit Trail</h3>
        <ul>
          {audit_items}
        </ul>
      </div>
    </article>
            """.strip()
        )

    html_document: str = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Clinical sEMG SOAP Report Summary</title>
  <style>
{_build_html_styles()}
  </style>
</head>
<body>
  <main class="container">
    <header class="report-header">
      <h1>Clinical sEMG-to-SOAP Report</h1>
      <p class="report-meta">
        Generated: {escape(timestamp)} |
        Total Assessments: {len(pairs)} |
        Guardrail Passed: {passed_count}/{len(pairs)}
      </p>
    </header>

    <section class="section-card" aria-labelledby="summary-heading">
      <h2 id="summary-heading" class="section-title">Guardrail Verification Summary</h2>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th scope="col">Patient ID</th>
              <th scope="col">Muscle Group</th>
              <th scope="col" class="num">Symmetry Index (%)</th>
              <th scope="col">Guardrail Status</th>
              <th scope="col">Verification Notes</th>
            </tr>
          </thead>
          <tbody>
            {"".join(summary_rows)}
          </tbody>
        </table>
      </div>
    </section>

    {"".join(patient_cards)}

    <footer class="report-footer">
      Synthetic sEMG clinical demonstration output &mdash; numeric biomarkers deterministically verified against input JSON.
    </footer>
  </main>
</body>
</html>
"""

    destination.write_text(html_document, encoding="utf-8")
    return destination
