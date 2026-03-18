---
name: "architecture-designer"
description: "Designs module boundaries, data flow, and contracts. Invoke when implementing multi-module features, refactoring architecture, or reducing coupling risks."
---

# Architecture Designer

## Purpose
Produce robust technical design that is implementable, testable, and evolution-friendly.

## Invoke When
- New feature spans backend, frontend, and data model.
- Current code has coupling, duplication, or unclear ownership.
- You need migration-safe interface changes.

## Workflow
1. Identify bounded contexts and ownership.
2. Define API contracts and state transitions.
3. Specify persistence schema and compatibility strategy.
4. Map failure modes and fallback behavior.
5. Propose phased rollout and verification points.

## Output Template
- Context map:
- Module responsibilities:
- API contracts:
- Data model changes:
- Compatibility strategy:
- Failure handling:
- Observability checkpoints:

## Quality Bar
- No hidden cross-layer side effects.
- Backward compatibility is explicit.
- Every major decision includes tradeoffs.
