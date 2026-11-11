# Coze / Dify 对接说明

这个目录用于说明如何把本仓库的 Prompt 和 API 复用到 Coze / Dify。

## 方案 A：Coze Bot + 插件

1. 新建 Bot，把 [`prompts/customer_service_agent.md`](../../prompts/customer_service_agent.md) 粘到人设与回复逻辑。
2. 建 3 个插件/工具：
   - `get_quote`：POST `http://your-host:8000/api/agent`，body `{"question": "..."}`（Demo 简化版）。
   - `get_order_status`：同上，用订单问题触发。
   - `create_handoff_ticket`：同上，用投诉问题触发。
3. 在 Bot 的「工具」里绑定插件。
4. 测试：报价、订单、投诉各 5 条。
5. 发布到飞书/企微/网页。

> 生产环境建议把报价、订单拆成独立 API，不要在 Agent 入口里复用同一个 `/api/agent`。

## 方案 B：Dify 工作流

```text
开始
  → 意图分类（FAQ / 报价 / 订单 / 投诉）
  → 分支
      FAQ：知识库检索 → LLM 回答（带引用）→ 置信度判断
      报价：参数抽取 → HTTP 请求报价 API → 结构化输出
      订单：订单号抽取 → HTTP 请求订单 API
      投诉：HTTP 请求工单 API → 返回工单号
  → 结束
```

知识库导入：

- 把 `data/customer_service/faq.jsonl` 的 `question` + `answer` 导入 Dify 知识库。
- 分段建议：按问答对分段，不要按固定长度硬切。
- 元数据：`group_id`、`category`、`source`、`synthetic=true`。
- 召回测试：用 `data/customer_service/eval_set.jsonl` 的 50 条 FAQ 做回归。

## 方案 C：直接调用本仓库

如果只是演示，直接用：

```bash
python -m ai_portfolio.web
```

打开 `http://127.0.0.1:8000`，四个 Tab 分别对应客服、内容、数据、投标。

## 注意事项

- 不要把 Coze/Dify 的“知识库命中”当成事实正确，仍要做引用和人工复核。
- 高风险场景（投诉、退款、合同）不要让 Bot 自主承诺。
- 生产环境需要鉴权、限流、日志、数据脱敏。
- Coze/Dify 的模型和插件能力会变化，落地前重新验证。
