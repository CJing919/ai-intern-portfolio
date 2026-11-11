import unittest
from pathlib import Path

from ai_portfolio.environment.bid import BidAssistant, summarize_file
from ai_portfolio.environment.process import analyze_process


class EnvironmentTest(unittest.TestCase):
    def test_bid_summary(self):
        path = Path("data/environment/bid_docs/2026_园区污水处理设备租赁项目_招标文件.md")
        summary = summarize_file(path)
        self.assertEqual(summary["project_id"], "SH-2026-WS-018")
        self.assertEqual(summary["budget_wan"], 186.0)
        self.assertTrue(summary["key_dates"])
        self.assertTrue(summary["qualifications"])
        self.assertTrue(summary["scoring"])
        self.assertFalse(any(item.startswith("#") for item in summary["qualifications"]))
        self.assertFalse(any("设备须具备远程监控" in item for item in summary["qualifications"]))
        self.assertTrue(any("ISO 9001" in item for item in summary["qualifications"]))

    def test_bid_retrieval(self):
        answer = BidAssistant().answer("投标截止时间是什么时候？")
        self.assertIn("2026-12-05", answer["answer"])
        self.assertTrue(answer["citations"])

    def test_bid_budget_and_deadline(self):
        answer = BidAssistant().answer("园区污水处理项目的投标截止时间和预算是什么？")
        self.assertIn("预算 186 万元", answer["answer"])
        self.assertIn("2026-12-20", answer["answer"])

    def test_process_ranking(self):
        result = analyze_process()
        self.assertEqual(result["steps"], 19)
        self.assertEqual(len(result["flows"]), 4)
        self.assertEqual(len(result["top_opportunities"]), 6)
        self.assertGreater(result["total_monthly_hours"], result["total_automatable_hours"])
        self.assertTrue(result["top_opportunities"][0]["priority_score"] >= result["top_opportunities"][-1]["priority_score"])


if __name__ == "__main__":
    unittest.main()
