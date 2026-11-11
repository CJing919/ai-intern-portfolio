# Prompt 索引

| 文件 | 用途 | 对应代码 |
| --- | --- | --- |
| `customer_service_agent.md` | 客服 Agent 的系统提示与工具规则 | `ai_portfolio/rag/agent.py` |
| `content_writer.md` | 内容 Brief/脚本/配图提示词生成 | `ai_portfolio/content/pipeline.py` |
| `bid_extractor.md` | 招标文件结构化抽取 | `ai_portfolio/environment/bid.py` |
| `eval_rubric.md` | 人工/LLM 评测 rubric | `ai_portfolio/rag/eval.py` |

## 使用建议

1. 先把 Prompt 当“产品规格”，不是“咒语”：写清楚输入、输出、边界、失败处理。
2. 任何 Prompt 变更都要跑同一套评测，避免“感觉更好”。
3. 高风险场景必须有确定性规则或人工节点，不能只靠 Prompt。
4. 生产环境要加 Prompt 注入防护、PII 脱敏和输出审核。
