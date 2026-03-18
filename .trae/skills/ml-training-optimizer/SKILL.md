---
name: "ml-training-optimizer"
description: "Optimizes ML training loops, features, and hyperparameters. Invoke when model quality is unstable, training is slow, or prediction quality needs improvement."
---

# ML Training Optimizer

## Purpose
Improve model training quality, stability, and reproducibility for production-grade quantitative workflows.

## Invoke When
- Model metrics fluctuate across runs.
- Training time is high or resource usage is unstable.
- You need stronger generalization before promotion.

## Workflow
1. Audit dataset construction, label horizon, and feature drift.
2. Validate train/validation split logic for temporal integrity.
3. Tune model and regularization with controlled search spaces.
4. Add threshold calibration and class-imbalance handling.
5. Produce promotion criteria and rollback-safe release rules.

## Output Template
- Data quality findings:
- Split and leakage check:
- Hyperparameter optimization plan:
- Metrics and calibration plan:
- Promotion gate:
- Rollback plan:

## Quality Bar
- Improvements are measured on out-of-sample periods.
- Tuning process is reproducible with fixed random seeds.
- Promotion decisions are tied to explicit guardrails.
