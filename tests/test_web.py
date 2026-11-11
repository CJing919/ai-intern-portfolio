import json
import threading
import unittest
from urllib.request import Request, urlopen

from ai_portfolio.web import make_server


class WebDemoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def _post(self, path, payload):
        req = Request(
            self.base + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_health(self):
        with urlopen(self.base + "/api/health", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["synthetic"])

    def test_index(self):
        with urlopen(self.base + "/", timeout=5) as response:
            html = response.read().decode("utf-8")
        self.assertIn("AI 产品 / Agent 作品集", html)

    def test_agent_api(self):
        data = self._post("/api/agent", {"question": "租赁 2 台移动式污水处理设备 10 天多少钱？"})
        self.assertEqual(data["intent"], "quote")
        self.assertIn("get_quote", [call["name"] for call in data["tool_calls"]])

    def test_content_api(self):
        data = self._post("/api/content", {"topic": "环保设备租赁如何选型", "channel": "公众号", "audience": "环保工程公司"})
        self.assertEqual(data["status"], "ready_for_review")
        self.assertIn("compliance", data)


if __name__ == "__main__":
    unittest.main()
