# n8n 对接说明

这个目录提供一个最小可用的 n8n 工作流模板：Webhook → 调用本地内容 API → 返回结果。

## 前提

1. 本地已启动 Web Demo：

```bash
python -m ai_portfolio.web
```

2. n8n 可以访问 `http://host.docker.internal:8000`（Docker）或 `http://127.0.0.1:8000`（本机）。

## 导入

1. n8n → Workflows → Import from File → 选择 `content_workflow.json`。
2. 检查 `Call Content API` 的 URL。
3. 激活 workflow，向 `POST /webhook/content-brief` 发送：

```json
{
  "topic": "污水设备租赁的 5 个成本坑",
  "channel": "公众号",
  "audience": "制造企业 EHS"
}
```

## 生产化建议

- 加鉴权（Header Auth / n8n credential），不要把 API 裸露在公网。
- 加超时、重试、错误分支。
- 生成结果推送到飞书/企微，进入人工审核，而不是直接发布。
- 记录每次请求的输入、输出、审核结果，便于复盘。
- 内容生成后必须过合规检查。
