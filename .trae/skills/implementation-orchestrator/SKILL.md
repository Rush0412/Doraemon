---
name: "implementation-orchestrator"
description: "Transforms approved design into ordered implementation steps. Invoke when executing multi-step delivery with dependencies across frontend, backend, and data."
---

# Implementation Orchestrator

## Purpose
Drive delivery with minimal rework by sequencing changes and validations correctly.

## Invoke When
- A change has three or more dependent implementation steps.
- Backend, frontend, and DB updates must stay synchronized.
- You need high-confidence rollout with checkpoints.

## Workflow
1. Build dependency graph of tasks.
2. Sequence by risk and blast radius.
3. Define contract-first coding order.
4. Add verification after each milestone.
5. Capture rollback-safe fallback points.

## Output Template
- Milestone plan:
- Dependency chain:
- Contract changes:
- Implementation order:
- Validation per milestone:
- Rollback notes:

## Quality Bar
- Each step leaves system runnable.
- Integration points are tested before moving on.
- No milestone completes without verification evidence.
