# 检索与 Agent 评测报告

> 由 `python -m ai_portfolio.cli eval` 自动生成。数据为合成数据，指标仅用于验证工程实现。

## 总览

| 指标 | 结果 |
| --- | ---: |
| 知识库文档数 | 210 |
| 评测用例数 | 60（FAQ 50） |
| Retrieval Hit@1 | 92.0% |
| Retrieval Hit@3 | 92.0% |
| Retrieval MRR | 0.920 |
| 简单子集 Hit@3 | 100.0% |
| 困难子集 Hit@3 | 60.0% |
| 关键词基线 Hit@3 | 92.0% |
| 意图识别准确率 | 100.0% |
| 工具选择准确率 | 100.0% |
| 引用命中率 | 93.3% |
| 转人工准确率 | 100.0% |
| 平均响应时间 | 1.44 ms |

## Agent 失败案例（含引用未命中）

| 用例 | 期望意图 | 实际意图 | 期望工具 | 实际工具 | 引用命中 |
| --- | --- | --- | --- | --- | --- |
| eval-hard-03 | faq | faq | search_knowledge_base | search_knowledge_base | 否 |
| eval-hard-04 | faq | faq | search_knowledge_base | search_knowledge_base | 否 |
| eval-hard-09 | faq | faq | search_knowledge_base | search_knowledge_base | 否 |
| eval-hard-10 | faq | faq | search_knowledge_base | search_knowledge_base | 否 |

## 检索未命中案例

| 难度 | 问题 | 期望知识点 | 实际 Top3 |
| --- | --- | --- | --- |
| hard | 开票要几个点？ | tax | invoice |
| hard | 机器坏了，师傅多久能到？ | maintenance | delivery |
| hard | 设备被偷了怎么办？ | insurance | capacity, fault |
| hard | 晚还几天怎么算钱？ | penalty | capacity |

## 口径说明

- Hit@k 按 `group_id` 去重，同一知识点的不同改写只计一次。
- 简单子集使用 FAQ 同义改写；困难子集刻意避开关键词，例如“开票/发票”“被偷/丢失”。
- 关键词基线使用字符 token 的重合度，不含 BM25 的长度归一化。
- 工具准确率检查期望工具是否出现在 Agent 的 tool_calls 中。
- 所有延迟为本机单次运行结果，不代表生产环境 SLA。
