import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

sqlalchemy_module = types.ModuleType("sqlalchemy")
sqlalchemy_orm_module = types.ModuleType("sqlalchemy.orm")


class _Session:
    pass


sqlalchemy_orm_module.Session = _Session
sqlalchemy_module.orm = sqlalchemy_orm_module
sys.modules.setdefault("sqlalchemy", sqlalchemy_module)
sys.modules.setdefault("sqlalchemy.orm", sqlalchemy_orm_module)

sys.modules.setdefault("backend.app.crud", types.ModuleType("backend.app.crud"))
sys.modules.setdefault("backend.app.quant_data_utils", types.ModuleType("backend.app.quant_data_utils"))

quant_core_utils_module = types.ModuleType("backend.app.quant_core_utils")


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


quant_core_utils_module._safe_float = _safe_float
quant_core_utils_module.__all__ = ["_safe_float"]
sys.modules.setdefault("backend.app.quant_core_utils", quant_core_utils_module)

strategies_module = types.ModuleType("backend.app.strategies")


class _MacdCrossBuy:
    pass


class _MacdCrossSell:
    pass


strategies_module.MacdCrossBuy = _MacdCrossBuy
strategies_module.MacdCrossSell = _MacdCrossSell
sys.modules.setdefault("backend.app.strategies", strategies_module)

import backend.app.quant_backtest_utils as quant_backtest_utils
from backend.app.quant_backtest_utils import (
    _build_commission_dict,
    _slippage_classes_from_bp,
    _summary_from_ranked_symbols,
)


class _DummyOrder:
    def __init__(self, *, buy_cnt, buy_price, sell_price):
        self.buy_cnt = buy_cnt
        self.buy_price = buy_price
        self.sell_price = sell_price


class QuantBacktestUtilsTestCase(unittest.TestCase):
    def test_build_commission_dict_applies_min_commission_and_stamp_tax(self):
        commission_dict = _build_commission_dict(
            {
                "commission_rate": 0.001,
                "min_commission": 5.0,
                "stamp_tax_rate": 0.001,
            }
        )
        order = _DummyOrder(buy_cnt=100, buy_price=10.0, sell_price=12.0)

        self.assertAlmostEqual(commission_dict["buy_commission_func"](order), 5.0)
        self.assertAlmostEqual(commission_dict["sell_commission_func"](order), 6.2)

    def test_build_commission_dict_handles_empty_args(self):
        commission_dict = _build_commission_dict({})

        self.assertEqual(commission_dict["buy_commission_func"](), 0.0)
        self.assertEqual(commission_dict["sell_commission_func"](), 0.0)

    def test_slippage_classes_from_bp_returns_none_when_abupy_missing(self):
        with patch.object(quant_backtest_utils, "AbuSlippageBuyMean", None), patch.object(
            quant_backtest_utils, "AbuSlippageSellMean", None
        ):
            buy_cls, sell_cls = _slippage_classes_from_bp(2)

        self.assertIsNone(buy_cls)
        self.assertIsNone(sell_cls)

    def test_summary_from_ranked_symbols_aggregates_cost_and_risk_metrics(self):
        rows = [
            {
                "symbol": "SH600036",
                "win_rate": 62.0,
                "sharpe": 1.4,
                "sortino": 1.8,
                "calmar": 1.2,
                "max_drawdown": 0.12,
                "annual_return": 0.18,
                "profit_sum": 12000.0,
                "commission_total": 320.0,
                "estimated_slippage_cost": 180.0,
                "estimated_total_cost": 500.0,
                "closed_orders": 12,
            },
            {
                "symbol": "SZ300750",
                "win_rate": 58.0,
                "sharpe": 1.1,
                "sortino": 1.5,
                "calmar": 0.9,
                "max_drawdown": 0.16,
                "annual_return": 0.14,
                "profit_sum": 8000.0,
                "commission_total": 280.0,
                "estimated_slippage_cost": 120.0,
                "estimated_total_cost": 400.0,
                "closed_orders": 10,
            },
        ]

        summary = _summary_from_ranked_symbols(rows, {"market": "CN"})

        self.assertEqual(summary["market"], "CN")
        self.assertAlmostEqual(summary["win_rate"], 60.0)
        self.assertAlmostEqual(summary["sharpe"], 1.25)
        self.assertAlmostEqual(summary["sortino"], 1.65)
        self.assertAlmostEqual(summary["calmar"], 1.05)
        self.assertAlmostEqual(summary["max_drawdown"], 0.14)
        self.assertAlmostEqual(summary["annual_return"], 0.16)
        self.assertAlmostEqual(summary["profit_sum"], 20000.0)
        self.assertAlmostEqual(summary["commission_total"], 600.0)
        self.assertAlmostEqual(summary["estimated_slippage_cost"], 300.0)
        self.assertAlmostEqual(summary["estimated_total_cost"], 900.0)
        self.assertAlmostEqual(summary["estimated_gross_profit_sum"], 20900.0)
        self.assertEqual(summary["closed_orders"], 22)


if __name__ == "__main__":
    unittest.main()
