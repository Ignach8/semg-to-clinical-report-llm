# Clinical sEMG SOAP Report Summary

Generated: 2026-11-22 03:46 UTC | Total Assessments: 3

## Guardrail Verification Summary

| Patient ID | Muscle Group | Symmetry Index (%) | Guardrail Status | Notes |
| :--- | :--- | ---: | :--- | :--- |
| PAT_001 | Quadriceps femoris (vastus lateralis) | 35.4% | PASS | Initial draft rejected (2 NUMERIC_HALLUCINATION, 2 MISSING_CRITICAL_METRIC); regenerated report verified. |
| PAT_002 | Quadriceps femoris (vastus lateralis) | 11.2% | PASS | All sEMG biomarkers verified on initial pass. |
| PAT_003 | Lumbar paraspinal (erector spinae, L4-L5) | 2.4% | PASS | All sEMG biomarkers verified on initial pass. |

---

## Patient PAT_001 - Quadriceps femoris (vastus lateralis)

- **Dominant Side:** right
- **Bilateral Symmetry Index:** 35.4%
- **Guardrail Verification Status:** PASS

### sEMG Biomarker Table

| Biomarker | Left Channel | Right Channel | Units |
| :--- | ---: | ---: | :--- |
| RMS Amplitude | 123.6 | 86.4 | uV |
| Median Frequency (MDF) | 78.4 | 61.8 | Hz |
| Mean Frequency (MNF) | 91.2 | 73.5 | Hz |
| Fatigue Slope | -0.32 | -0.74 | Hz/s |
| Bilateral Symmetry Index | 35.4 | 35.4 | % |

### Structured SOAP Note

**Subjective**

Clinical context for patient PAT_001: Subacute post-stroke rehabilitation assessment during standardized isometric knee extension evaluating persistent right-sided lower-limb weakness and progressive myoelectric fatigue. No additional patient-reported symptoms were documented.

**Objective**

Muscle group evaluated: Quadriceps femoris (vastus lateralis). Dominant side: right. Left channel sEMG: RMS 123.6 uV, MDF 78.4 Hz, MNF 91.2 Hz, Fatigue Slope -0.32 Hz/s. Right channel sEMG: RMS 86.4 uV, MDF 61.8 Hz, MNF 73.5 Hz, Fatigue Slope -0.74 Hz/s. Bilateral Symmetry Index: 35.4%.

**Assessment**

Bilateral sEMG amplitude analysis demonstrates pronounced bilateral amplitude asymmetry (Bilateral Symmetry Index 35.4%), with reduced recruitment amplitude on the right side (86.4 uV) relative to the left side (123.6 uV). Frequency-domain analysis reveals pronounced spectral compression consistent with progressive myoelectric fatigue, with median frequency values of 78.4 Hz (left) and 61.8 Hz (right) and fatigue slopes of -0.32 Hz/s (left) and -0.74 Hz/s (right). Interpretation is strictly limited to the recorded sEMG biomarkers and documented clinical context.

**Plan**

Correlate objective sEMG findings for the Quadriceps femoris (vastus lateralis) with clinical physical examination by the supervising clinician. Perform serial follow-up sEMG reassessment under an identical testing protocol to monitor bilateral activation symmetry and myoelectric fatigue progression. Guide non-pharmacological rehabilitation or ergonomic load adjustments based on longitudinal neuromuscular response.

### Guardrail Audit Trail

- Initial draft rejected: NUMERIC_HALLUCINATION: Value '111.4 uV' does not match ground-truth uV biomarkers [86.4, 123.6] (tolerance +/-0.1).
- Initial draft rejected: NUMERIC_HALLUCINATION: Value '50.4%' does not match ground-truth % biomarkers [35.4] (tolerance +/-0.1).
- Initial draft rejected: MISSING_CRITICAL_METRIC: Right RMS (86.4 uV) was not found in the Objective section.
- Initial draft rejected: MISSING_CRITICAL_METRIC: Bilateral Symmetry Index (35.4%) was not found in the Objective section.
- Clean regeneration pass succeeded: all sEMG biomarkers verified.

---

## Patient PAT_002 - Quadriceps femoris (vastus lateralis)

- **Dominant Side:** right
- **Bilateral Symmetry Index:** 11.2%
- **Guardrail Verification Status:** PASS

### sEMG Biomarker Table

| Biomarker | Left Channel | Right Channel | Units |
| :--- | ---: | ---: | :--- |
| RMS Amplitude | 141.6 | 158.4 | uV |
| Median Frequency (MDF) | 76.5 | 81.2 | Hz |
| Mean Frequency (MNF) | 89.4 | 94.6 | Hz |
| Fatigue Slope | -0.14 | -0.09 | Hz/s |
| Bilateral Symmetry Index | 11.2 | 11.2 | % |

### Structured SOAP Note

**Subjective**

Clinical context for patient PAT_002: Six-month post-operative follow-up after left anterior cruciate ligament (ACL) reconstruction during standardized isometric knee extension testing to assess residual quadriceps asymmetry and endurance. No additional patient-reported symptoms were documented.

**Objective**

Muscle group evaluated: Quadriceps femoris (vastus lateralis). Dominant side: right. Left channel sEMG: RMS 141.6 uV, MDF 76.5 Hz, MNF 89.4 Hz, Fatigue Slope -0.14 Hz/s. Right channel sEMG: RMS 158.4 uV, MDF 81.2 Hz, MNF 94.6 Hz, Fatigue Slope -0.09 Hz/s. Bilateral Symmetry Index: 11.2%.

**Assessment**

Bilateral sEMG amplitude analysis demonstrates mild residual bilateral amplitude asymmetry (Bilateral Symmetry Index 11.2%), with reduced recruitment amplitude on the left side (141.6 uV) relative to the right side (158.4 uV). Frequency-domain analysis reveals minimal negative spectral shift consistent with preserved short-term endurance, with median frequency values of 76.5 Hz (left) and 81.2 Hz (right) and fatigue slopes of -0.14 Hz/s (left) and -0.09 Hz/s (right). Interpretation is strictly limited to the recorded sEMG biomarkers and documented clinical context.

**Plan**

Correlate objective sEMG findings for the Quadriceps femoris (vastus lateralis) with clinical physical examination by the supervising clinician. Perform serial follow-up sEMG reassessment under an identical testing protocol to monitor bilateral activation symmetry and myoelectric fatigue progression. Guide non-pharmacological rehabilitation or ergonomic load adjustments based on longitudinal neuromuscular response.

### Guardrail Audit Trail

- Passed deterministic numeric verification on initial pass with zero violations.

---

## Patient PAT_003 - Lumbar paraspinal (erector spinae, L4-L5)

- **Dominant Side:** right
- **Bilateral Symmetry Index:** 2.4%
- **Guardrail Verification Status:** PASS

### sEMG Biomarker Table

| Biomarker | Left Channel | Right Channel | Units |
| :--- | ---: | ---: | :--- |
| RMS Amplitude | 98.8 | 101.2 | uV |
| Median Frequency (MDF) | 58.6 | 57.9 | Hz |
| Mean Frequency (MNF) | 69.8 | 68.9 | Hz |
| Fatigue Slope | -1.18 | -1.24 | Hz/s |
| Bilateral Symmetry Index | 2.4 | 2.4 | % |

### Structured SOAP Note

**Subjective**

Clinical context for patient PAT_003: Occupational ergonomics neuromuscular fatigue evaluation during a sustained static isometric trunk extension task following prolonged manual material handling. No additional patient-reported symptoms were documented.

**Objective**

Muscle group evaluated: Lumbar paraspinal (erector spinae, L4-L5). Dominant side: right. Left channel sEMG: RMS 98.8 uV, MDF 58.6 Hz, MNF 69.8 Hz, Fatigue Slope -1.18 Hz/s. Right channel sEMG: RMS 101.2 uV, MDF 57.9 Hz, MNF 68.9 Hz, Fatigue Slope -1.24 Hz/s. Bilateral Symmetry Index: 2.4%.

**Assessment**

Bilateral sEMG amplitude analysis demonstrates symmetric bilateral activation amplitude (Bilateral Symmetry Index 2.4%), with comparable recruitment amplitude between the left side (98.8 uV) and right side (101.2 uV). Frequency-domain analysis reveals pronounced spectral compression consistent with progressive myoelectric fatigue, with median frequency values of 58.6 Hz (left) and 57.9 Hz (right) and fatigue slopes of -1.18 Hz/s (left) and -1.24 Hz/s (right). Interpretation is strictly limited to the recorded sEMG biomarkers and documented clinical context.

**Plan**

Correlate objective sEMG findings for the Lumbar paraspinal (erector spinae, L4-L5) with clinical physical examination by the supervising clinician. Perform serial follow-up sEMG reassessment under an identical testing protocol to monitor bilateral activation symmetry and myoelectric fatigue progression. Guide non-pharmacological rehabilitation or ergonomic load adjustments based on longitudinal neuromuscular response.

### Guardrail Audit Trail

- Passed deterministic numeric verification on initial pass with zero violations.

---
