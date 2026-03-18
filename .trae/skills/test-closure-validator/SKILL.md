---
name: "test-closure-validator"
description: "Builds end-to-end verification from unit to acceptance tests. Invoke before delivery, after major refactors, or when regressions appear."
---

# Test Closure Validator

## Purpose
Establish full verification closure from correctness to reliability and user acceptance.

## Invoke When
- Feature work is complete and ready for release.
- Refactor risk requires regression protection.
- Incidents reveal missing test coverage or weak checks.

## Workflow
1. Define quality gates by layer: unit, API, integration, E2E.
2. Create test matrix with positive, negative, boundary, and recovery cases.
3. Validate observability: logs, errors, metrics, and traces.
4. Check non-functional constraints: latency, stability, resilience.
5. Produce release readiness verdict with blockers.

## Output Template
- Scope under test:
- Test matrix:
- Runtime evidence:
- Defects and severity:
- Residual risks:
- Release recommendation:

## Quality Bar
- All critical paths have deterministic checks.
- Failure scenarios are reproducible.
- Release advice is based on evidence, not assumptions.
