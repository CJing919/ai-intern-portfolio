# JD 逐条映射

> 目标岗位：上海强昕环保科技 · AI 实习生（AI 产品 / Agent 方向）。
> 本文件把 JD 的每一条要求，映射到仓库中的代码、数据、文档或可演示结果。面试时按“JD 关键词 → 我的证据 → 我学到什么”讲，不要只背功能。

## 一、岗位背景

JD 的核心背景是：公司处于环保 / 循环经济行业，正在推进企业 AI 化转型，希望通过 **AI Agent + 自动化** 重构业务流程，让团队从重复性工作中释放出来。

**本仓库的回应**：不是做一个“通用聊天机器人”，而是围绕环保设备租赁的真实业务链路，拆出客服、内容、数据、投标、流程五类场景，并用可运行 Demo 证明“业务拆解 → Agent/Workflow → 评测 → 落地”的完整路径。

## 二、岗位要求

| JD 要求 | 本仓库证据 | 面试怎么讲 |
| --- | --- | --- |
| 本科及以上，计算机 / 人工智能 / 信息管理 / 产品管理相关专业优先 | 简历教育背景为信息管理与信息系统；仓库体现产品 + 技术的复合能力 | 用“信息管理 + 产品实践”解释为什么能做业务翻译 |
| 985 / 211 / 海外院校优先 | 简历中的学校信息 | 一句话带过，不展开 |
| 有产品经理经验或 AI 应用经验 | 3 份 PRD、用户访谈、竞品分析、评测方案；3 个可运行 Demo | 重点讲“我怎么定义问题、怎么验收”，而不是只讲工具 |
| 对 LLM、AI Agent、AI 自动化有强兴趣 | `docs/ARCHITECTURE.md`、`docs/EVALUATION.md`、`docs/ROADMAP.md` | 讲清楚 Agent 的能力边界：什么时候用 RAG，什么时候用工具，什么时候必须转人工 |
| 熟悉 ChatGPT、Claude、Gemini、Midjourney、Runway | `docs/COMPETITOR_ANALYSIS.md`、`prompts/content_writer.md` | 讲不同模型的分工：长文/推理、图片/视频、成本与合规 |
| 理解 Prompt Engineering、RAG、Agent、Workflow | `ai_portfolio/rag/`、`ai_portfolio/content/`、`prompts/` | 用“检索 → 工具 → 引用 → 置信度 → 转人工”讲一个完整链路 |
| 逻辑能力强，能把复杂流程拆成任务 | `docs/PROCESS_MAPS.md`、`ai_portfolio/environment/process.py`、`reports/process_opportunities.md` | 讲“流程节点 → 工时 → 自动化潜力 → 风险 → 优先级”的拆法 |
| 学习能力强，愿意持续探索新 AI 工具 | `docs/ROADMAP.md`、`integrations/n8n/`、`integrations/coze/` | 讲你如何在一周内搭出原型、如何做工具选型 |

## 三、岗位职责

### 1. 负责公司 AI 应用产品设计：内容生产、客服回复、营销运营、数据分析、自动化办公

| 场景 | 仓库实现 | 关键设计 |
| --- | --- | --- |
| 客服回复 | 客服 RAG Agent | 意图路由、知识库检索、报价/订单工具、引用、转人工 |
| 内容生产 | 内容 Workflow | Brief、3 个标题、脚本、配图提示词、合规检查、审核状态 |
| 营销运营 | 内容数据看板 + 渠道/选题分析 | 渠道 CPL、线索转化、周环比、Top 选题 |
| 数据分析 | 自然语言数据问答 | 规则化意图到指标聚合，输出结论和数据 |
| 自动化办公 | 招标文件摘要 + 流程机会矩阵 | 关键日期/预算/资质/评分/风险抽取，流程优先级排序 |

**面试讲法**：先讲“为什么选这五个场景”（高频、重复、可衡量、风险可控），再讲每个场景的输入、输出、人工接管点和验收指标。

### 2. 梳理各部门业务流程，识别可通过 AI 自动化优化的环节

- 流程图：[`docs/PROCESS_MAPS.md`](PROCESS_MAPS.md)
- 数据：[`data/environment/process_steps.csv`](../data/environment/process_steps.csv)
- 分析：[`reports/process_opportunities.md`](../reports/process_opportunities.md)

仓库把流程拆成 4 条链路、19 个节点，按“月工时 × 自动化潜力 × 数据就绪度 / 风险”排序，输出 Top 6 机会点。高风险节点（投诉、合同用印）明确建议“AI 辅助 + 人工复核”，不直接自动化。

### 3. 设计 AI 工作流（AI Workflow）：内容生成、客服自动回复、营销自动化、数据分析助手

- 客服自动回复：`ai_portfolio/rag/agent.py`
- 内容生成：`ai_portfolio/content/pipeline.py`
- 营销/数据分析：`ai_portfolio/content/analytics.py`
- 可视化：`ai_portfolio/web.py` 的四个 Tab

每个工作流都有明确的 **输入、处理节点、输出、失败兜底**，而不是只画一张概念图。

### 4. 设计 AI Agent 系统结构：任务拆解、工具调用、知识库、自动化流程

- 任务拆解：意图路由 + 槽位抽取（设备、数量、天数、距离、订单号）
- 工具调用：`get_quote`、`get_order_status`、`create_handoff_ticket`、`search_knowledge_base`
- 知识库：210 条 FAQ、BM25、按 `group_id` 去重、引用返回
- 自动化流程：内容 Workflow、投标摘要、流程机会分析
- 质量：60 条评测、失败案例分析、23 个单元测试

**面试讲法**：不要只讲“我用了 Dify/Coze”。要讲“为什么这个场景用 RAG + 工具，而不是让 LLM 自由回答”；以及“什么情况下必须转人工”。

### 5. 与 AI 工程师协作，推动 AI 系统开发和落地

仓库模拟了产品与工程的协作产物：

- 工具 JSON Schema：[`data/customer_service/tool_schemas.json`](../data/customer_service/tool_schemas.json)
- 评测口径：[`docs/EVALUATION.md`](EVALUATION.md)
- CI：[`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
- 可复现报告：[`reports/`](../reports/)

**面试讲法**：产品经理不是“提需求就结束”，而是要把验收标准写成工程师能执行的东西：输入输出、失败码、置信度阈值、人工接管、评测集、回归门槛。

### 6. 持续跟踪 AI 技术发展，优化 AI 应用方案

- 竞品与工具选型：[`docs/COMPETITOR_ANALYSIS.md`](COMPETITOR_ANALYSIS.md)
- 路线图：[`docs/ROADMAP.md`](ROADMAP.md)
- 失败分析：[`docs/EVALUATION.md`](EVALUATION.md)

**面试讲法**：讲一个你最近试过的新工具，以及“试用 → 判断边界 → 是否进入生产”的决策过程。

## 四、加分项

| 加分项 | 仓库证据 |
| --- | --- |
| AI 产品设计经验 | 3 份 PRD、用户访谈、竞品分析 |
| AI 自动化流程经验 | 内容 Workflow、流程机会矩阵、n8n 对接说明 |
| 使用过 Dify / Coze / Flowise / n8n | `integrations/`、架构文档中的选型对比 |
| 有 AI 项目经验 | 3 个可运行 Demo + 评测 + 测试 |
| 有 AI 创业项目经验 | 仓库按“可展示、可复现、可讲述”的方式组织，可作为创业/个人项目材料 |

## 五、面试时的 90 秒版本

> “我做过一个面向环保设备租赁的 AI 应用作品集。它不是单纯接一个大模型，而是把业务拆成客服、内容、数据、投标四类场景：客服用 RAG + 工具调用，报价和订单走确定性工具，投诉转人工；内容用 Workflow 做 Brief、脚本、配图提示词和合规检查；数据用自然语言问答做渠道和选题分析；投标用结构化抽取做日期、预算、资质和评分条款。  
> 我建了 210 条知识库和 60 条评测，当前检索 Hit@1 是 92%，意图和工具选择是 100%，困难子集只有 60%，失败主要在口语化同义词，所以下一步会做 query expansion 和真实用户日志回流。  
> 这个项目最能说明的是：我能把模糊的业务问题拆成可验收的 Agent/Workflow，而不是只停留在画原型。”

## 六、不要这样说

- ❌ “这是我在某环保公司真实上线的系统。”——仓库是合成数据 Demo，不能这样讲。
- ❌ “我们的准确率 100%。”——这是 60 条合成评测上的结果，不是生产准确率。
- ❌ “用了 Dify/Coze 就说明我会 AI 产品。”——工具只是实现手段，面试官更关心你如何定义问题、拆流程、做评测和兜底。

