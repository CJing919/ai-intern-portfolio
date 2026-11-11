import unittest

from ai_portfolio.rag.eval import evaluate


class EvaluationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate()

    def test_retrieval_quality_floor(self):
        metrics = self.report["metrics"]
        self.assertGreaterEqual(metrics["retrieval_hit_at_3"], 0.85)
        self.assertGreaterEqual(metrics["retrieval_hit_at_1"], 0.85)

    def test_agent_routing_quality_floor(self):
        metrics = self.report["metrics"]
        self.assertGreaterEqual(metrics["intent_accuracy"], 0.95)
        self.assertGreaterEqual(metrics["tool_accuracy"], 0.95)
        self.assertGreaterEqual(metrics["citation_hit_rate"], 0.9)

    def test_report_contains_baseline(self):
        self.assertIn("keyword_baseline_hit_at_3", self.report["metrics"])


if __name__ == "__main__":
    unittest.main()
