import unittest

from ai_portfolio.text import parse_int, parse_quantity, tokenize


class TextTest(unittest.TestCase):
    def test_tokenize_chinese_and_latin(self):
        tokens = tokenize("污水处理设备租赁 12 个月，支持 MQTT")
        self.assertIn("污水", tokens)
        self.assertIn("租赁", tokens)
        self.assertIn("mqtt", tokens)
        self.assertIn("12", tokens)

    def test_parse_chinese_numbers(self):
        self.assertEqual(parse_int("十二"), 12)
        self.assertEqual(parse_int("三十"), 30)
        self.assertEqual(parse_int("两"), 2)
        self.assertEqual(parse_quantity("租 3 台设备", default=1), 3)
        self.assertEqual(parse_quantity("两台设备", default=1), 2)


if __name__ == "__main__":
    unittest.main()
