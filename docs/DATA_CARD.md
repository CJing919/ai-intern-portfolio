# 数据卡（Data Card）

## 1. 结论先行

- **所有数据均为合成数据**，由 `scripts/generate_data.py` 确定性生成，或以 Markdown 手工编写。
- 不包含任何真实客户、真实订单、真实价格、真实政策或真实个人信息。
- 数据仅用于验证代码路径、产品流程和评测方法，不能用于真实业务决策。
- 仓库中的公司名、项目名、金额、日期、资质要求均为虚构。

## 2. 数据清单

| 数据集 | 路径 | 规模 | 生成方式 | 用途 |
| --- | --- | ---: | --- | --- |
| 客服 FAQ | `data/customer_service/faq.jsonl` | 210 条 | 30 个知识点 × 7 种问法 | RAG 检索、客服 Agent |
| 评测集 | `data/customer_service/eval_set.jsonl` | 60 条 | 50 条 FAQ + 10 条工具/转人工 | 检索、意图、工具、引用评测 |
| 订单 | `data/customer_service/orders.json` | 8 条 | 手写合成 | 订单查询工具 |
| 价格表 | `data/customer_service/pricing.json` | 8 类设备 | 手写合成 | 报价工具 |
| 工具 Schema | `data/customer_service/tool_schemas.json` | 4 个工具 | 手写 | 模拟 Function Calling |
| 内容日历 | `data/content/calendar.csv` | 30 条 | 确定性生成 | 内容排期 |
| 内容表现 | `data/content/performance.csv` | 90 条 / 30 天 | 确定性生成 | 渠道、选题、CPL 分析 |
| 招标文件 | `data/environment/bid_docs/*.md` | 3 份 | 手写合成 | 摘要与检索 |
| 流程节点 | `data/environment/process_steps.csv` | 19 个节点 / 4 条流程 | 手写合成 | 自动化机会排序 |

## 3. FAQ 数据结构

```json
{
  "id": "faq-deposit-01",
  "group_id": "deposit",
  "category": "押金",
  "question": "租赁设备需要交多少押金？",
  "answer": "押金通常按设备原值的 10%—20% 收取……",
  "tags": ["押金", "退款", "验收"],
  "source": "synthetic-faq-v1",
  "synthetic": true
}
```

设计说明：

- `group_id` 用于把同一知识点的 7 种问法归为一组，评测时按组去重，避免“同一答案占满 Top3”。
- `question` 是用户可能的各种问法，`answer` 是标准答案。
- `tags` 用于检索增强和可解释性。
- `synthetic: true` 是显式标记，任何下游使用都能识别。

## 4. 评测集结构

```json
{
  "id": "eval-hard-03",
  "question": "开票要几个点？",
  "expected_groups": ["tax"],
  "expected_intent": "faq",
  "expected_tool": "search_knowledge_base",
  "difficulty": "hard"
}
```

- 40 条简单同义改写：验证基础召回。
- 10 条困难口语化问法：刻意避开关键词，例如“开票/发票”“被偷/丢失”“晚还/逾期”。
- 10 条工具/转人工用例：验证报价、订单、投诉路由。
- 困难子集当前 Hit@3 为 60%，失败案例保留在评测报告中，作为下一步优化依据。

## 5. 内容数据

`performance.csv` 字段：

| 字段 | 含义 | 合成规则 |
| --- | --- | --- |
| `date` | 日期 | 2026-08-01 至 2026-08-30 |
| `channel` | 渠道 | 公众号 / 小红书 / 视频号 |
| `content_type` | 内容类型 | 图文 / 短视频 / 案例 |
| `topic` | 选题 | 30 个环保设备租赁相关选题 |
| `views` | 曝光 | 按渠道区间 + 周趋势生成 |
| `likes` / `comments` / `shares` | 互动 | 按曝光 × 互动率拆分 |
| `leads` | 线索 | 按曝光 × 渠道转化率生成 |
| `spend` | 投放成本 | 按渠道区间生成 |

这些数据用于验证“渠道对比、CPL、周环比、Top 选题”这些分析逻辑，不是行业基准。

## 6. 招标文件

3 份合成招标文件覆盖：

1. 园区污水处理设备租赁：预算 186 万元，12 个月，一级 A 标准。
2. 街道扬尘噪声监测服务：预算 68 万元，15 个点位，平台联网。
3. 工业园废气治理运维：预算 240 万元，3 套设施，2 小时响应。

每份文件都包含项目概况、资格要求、技术需求、商务要求、交付运维、评分办法、时间安排，用于测试结构化抽取。

## 7. 隐私与合规

- 不含真实姓名、电话、地址、身份证号、车牌号、客户合同。
- 订单中的客户名称为“上海某园区运营方”等泛化描述。
- 招标文件中的采购人、项目编号、金额均为虚构。
- 如果未来接入真实数据，必须增加：脱敏、访问控制、审计日志、数据保留期限、供应商数据处理协议。

## 8. 使用限制

- 不要把合成价格用于真实报价。
- 不要把合成政策用于真实补贴申请。
- 不要把合成评测指标写成生产准确率。
- 不要把 Demo 包装成真实企业项目。

## 9. 复现方式

```bash
python scripts/generate_data.py
python -m ai_portfolio.cli demo
```

生成脚本使用固定随机种子（`random.Random(42)`），同一环境下结果可复现。不同 Python 版本或浮点实现可能有极小差异。
