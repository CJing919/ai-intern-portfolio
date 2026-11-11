import unittest

from ai_portfolio.content.analytics import ContentAnalytics
from ai_portfolio.content.checks import check_content
from ai_portfolio.content.pipeline import ContentWorkflow


class ContentWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief = ContentWorkflow().generate("污水设备租赁的 5 个成本坑", "公众号", "制造企业 EHS")

    def test_brief_is_ready_for_review(self):
        self.assertEqual(self.brief.status, "ready_for_review")
        self.assertTrue(self.brief.titles)
        self.assertGreaterEqual(self.brief.compliance["score"], 80)
        self.assertIn("污水设备租赁", self.brief.script)

    def test_compliance_blocks_absolute_claim(self):
        result = check_content("我们保证 100% 通过验收，零风险，行业第一。")
        self.assertFalse(result["passed"])
        self.assertTrue(result["sensitive_hits"])
        self.assertLess(result["score"], 80)

    def test_analytics_summary(self):
        analytics = ContentAnalytics()
        summary = analytics.summary()
        self.assertEqual(summary["posts"], 90)
        self.assertGreater(summary["views"], 0)
        self.assertGreater(summary["leads"], 0)
        self.assertTrue(summary["by_channel"])
        self.assertTrue(summary["top_topics"])

    def test_analytics_question(self):
        answer = ContentAnalytics().answer_question("哪个渠道线索最多？")
        self.assertIn("线索最多", answer["answer"])
        self.assertIn("channel", answer["data"])


if __name__ == "__main__":
    unittest.main()
