---
name: "quant-strategy-reviewer"
description: "Reviews strategy logic for bias, leakage, and risk controls. Invoke when designing backtests, optimizing factors, or validating production readiness."
---

# Quant Strategy Reviewer

## Purpose
Audit quantitative strategy design quality before scaling to production use.

## Invoke When
- New strategy is proposed or existing strategy is refactored.
- Backtest results look unusually strong or unstable.
- You need risk-aware go or no-go decisions.

## Workflow
1. Check data integrity, timestamp alignment, and survivorship handling.
2. Inspect feature engineering for leakage.
3. Validate backtest protocol: slippage, fee, liquidity, and universe rules.
4. Examine overfitting risk with out-of-sample and regime splits.
5. Review risk controls: exposure, drawdown, concentration, turnover.

## Output Template
- Strategy hypothesis:
- Data assumptions:
- Leakage and bias checks:
- Robustness tests:
- Risk controls:
- Production readiness verdict:

## Quality Bar
- Strategy alpha remains after realistic transaction costs.
- Performance persists across regimes, not one period.
- Risk constraints are explicit and enforceable.
