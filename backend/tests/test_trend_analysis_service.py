import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app import schemas
from backend.app.trend_analysis_service import build_trend_analysis_demo


class TrendAnalysisServiceTestCase(unittest.TestCase):
    def test_demo_builds_structured_response(self):
        payload = schemas.TrendAnalysisDemoPayload(
            market="cn",
            symbol="600036",
            horizon_days=5,
            chart_image_name="招商银行-kline.png",
            chart_image_type="image/png",
            chart_image_size_kb=256.3,
            feature_rows=[
                {"trade_date": "2026-05-20", "close": 41.2, "ma5": 40.8, "ma20": 39.6, "rsi14": 60.4, "macd": 0.22},
                {"trade_date": "2026-05-21", "close": 41.9, "ma5": 41.0, "ma20": 39.9, "rsi14": 63.1, "macd": 0.31},
            ],
        )

        result = build_trend_analysis_demo(payload)

        self.assertEqual(result["symbol"], "600036")
        self.assertEqual(result["market"], "CN")
        self.assertTrue(result["chart_upload"]["attached"])
        self.assertEqual(result["feature_summary"]["rows"], 2)
        self.assertIn(result["analysis"]["direction"], {"bullish", "neutral"})
        self.assertEqual(result["architecture"]["data_contract_version"], "v1")
        self.assertTrue(result["architecture"]["next_stage_capabilities"])


if __name__ == "__main__":
    unittest.main()
