import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app import schemas


class SchemaContractsTestCase(unittest.TestCase):
    def test_kline_update_requires_scope_when_not_all(self):
        with self.assertRaises(ValidationError):
            schemas.KlineUpdatePayload(all=False, symbols=None)

    def test_analysis_payload_requires_symbols(self):
        with self.assertRaises(ValidationError):
            schemas.AnalysisPayload(tool="support_resistance")

    def test_manual_symbols_payload_normalizes_fields(self):
        payload = schemas.ManualSymbolsPayload(
            market="cn",
            symbols=[{"symbol": "sz300750", "name": "宁德时代"}],
        )
        self.assertEqual(payload.market, "CN")
        self.assertEqual(payload.symbols[0].symbol, "SZ300750")
        self.assertEqual(payload.symbols[0].market, "CN")

    def test_trend_analysis_demo_requires_input_source(self):
        with self.assertRaises(ValidationError):
            schemas.TrendAnalysisDemoPayload(symbol="600036", feature_rows=[])


if __name__ == "__main__":
    unittest.main()
