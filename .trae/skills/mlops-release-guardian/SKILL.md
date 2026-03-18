---
name: "mlops-release-guardian"
description: "Builds ML release gates and monitoring policies. Invoke when promoting models, setting rollback criteria, or validating online prediction safety."
---

# MLOps Release Guardian

## Purpose
Establish safe model promotion, observability, and rollback controls for live quant systems.

## Invoke When
- A model is ready for promotion to active.
- You need online monitoring and alert thresholds.
- You need formal rollback rules for performance degradation.

## Workflow
1. Define offline-to-online consistency checks.
2. Set promotion thresholds and confidence intervals.
3. Configure runtime monitors for drift, latency, and error rates.
4. Define staged rollout and rollback triggers.
5. Produce release checklist and incident response runbook.

## Output Template
- Promotion criteria:
- Canary and rollout plan:
- Online monitoring metrics:
- Alert thresholds:
- Rollback triggers:
- Incident response:

## Quality Bar
- Every promotion has objective acceptance thresholds.
- Monitoring covers quality, reliability, and data drift.
- Rollback path is automated or operationally simple.
