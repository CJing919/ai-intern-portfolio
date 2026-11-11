import unittest

from ai_portfolio.rag.agent import CustomerServiceAgent
from ai_portfolio.rag.retriever import KnowledgeBase


class RagAgentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase.from_jsonl()
        cls.agent = CustomerServiceAgent(cls.kb)

    def test_knowledge_base_size_and_search(self):
        self.assertEqual(len(self.kb), 210)
        hits = self.kb.search("设备租赁押金一般交多少？", top_k=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0].document.group_id, "deposit")

    def test_faq_answer_has_citation(self):
        result = self.agent.answer("租赁设备需要交多少押金？")
        self.assertEqual(result.intent, "faq")
        self.assertFalse(result.handoff)
        self.assertTrue(result.citations)
        self.assertIn("押金", result.answer)

    def test_quote_calls_tool(self):
        result = self.agent.answer("租赁 2 台移动式污水处理设备 10 天，大概多少钱？")
        self.assertEqual(result.intent, "quote")
        self.assertIn("get_quote", [call.name for call in result.tool_calls])
        self.assertIn("含税合计", result.answer)
        self.assertIn("押金", result.answer)

    def test_order_lookup(self):
        result = self.agent.answer("订单 EQ2026003 现在什么进度？")
        self.assertEqual(result.intent, "order")
        self.assertIn("get_order_status", [call.name for call in result.tool_calls])
        self.assertIn("物流运输", result.answer)

    def test_complaint_creates_handoff(self):
        result = self.agent.answer("设备故障三天没人处理，我要投诉，转人工")
        self.assertTrue(result.handoff)
        self.assertTrue(result.handoff_ticket.startswith("HO-"))
        self.assertIn("create_handoff_ticket", [call.name for call in result.tool_calls])

    def test_low_confidence_question_handoffs(self):
        result = self.agent.answer("你们公司明天股票会涨吗？")
        self.assertTrue(result.handoff)


if __name__ == "__main__":
    unittest.main()
