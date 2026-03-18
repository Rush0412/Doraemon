---
name: "adversarial-robustness-auditor"
description: "Assesses robustness against adversarial and distribution-shift risks. Invoke when adding adversarial training, stress testing models, or hardening production inference."
---

# Adversarial Robustness Auditor

## Purpose
Evaluate and harden ML pipelines against adversarial perturbation, noisy data, and regime shifts.

## Invoke When
- You plan adversarial training or robust optimization.
- Model performance collapses under stressed market conditions.
- Inference outputs are sensitive to small feature perturbations.

## Workflow
1. Define attack surfaces in features, labels, and ingestion paths.
2. Simulate perturbation and shift scenarios with reproducible seeds.
3. Measure robustness degradation and confidence instability.
4. Recommend defenses: robust loss, clipping, feature guards, ensemble checks.
5. Define runtime monitors and fail-safe fallback policies.

## Output Template
- Threat model:
- Attack simulation plan:
- Robustness metrics:
- Defense options:
- Runtime guardrails:
- Residual risks:

## Quality Bar
- Robustness is tested under multiple perturbation levels.
- Defenses improve stability without unacceptable alpha decay.
- Production safeguards detect and contain abnormal inference behavior.
