"""Reproducible content-production workflow.

The workflow mirrors the resume project: brief -> draft -> compliance check ->
review package. The default writer is template-based so the demo runs offline;
the same interface can be replaced by Coze / n8n / an LLM call.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

from .checks import check_content

CHANNEL_TIPS = {
    "公众号": "适合完整方法论：开头给结论，中段用清单，结尾引导领取模板。",
    "小红书": "前 2 行给钩子，正文短句分段，配图突出对比和清单。",
    "视频号": "前 3 秒给冲突，口播每段不超过 2 句，字幕强调数字和动作。",
}

TITLE_TEMPLATES = [
    "{topic}：一份可落地的检查清单",
    "关于{topic}，签合同前先确认这 3 件事",
    "{topic}：从选型到退租的完整流程",
]


@dataclass
class ContentBrief:
    topic: str
    channel: str
    audience: str
    tone: str
    titles: list[str]
    hook: str
    outline: list[str]
    script: str
    image_prompt: str
    hashtags: list[str]
    cta: str
    compliance: dict
    status: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def as_dict(self) -> dict:
        return asdict(self)

    def to_markdown(self) -> str:
        titles = "\n".join(f"{i}. {t}" for i, t in enumerate(self.titles, start=1))
        outline = "\n".join(f"{i}. {t}" for i, t in enumerate(self.outline, start=1))
        issues = "\n".join(f"- {x}" for x in self.compliance["issues"]) or "- 无"
        return f"""# {self.topic}

- 渠道：{self.channel}
- 人群：{self.audience}
- 语气：{self.tone}
- 状态：{self.status}
- 合规评分：{self.compliance['score']}/100

## 标题备选
{titles}

## 开头钩子
{self.hook}

## 内容结构
{outline}

## 正文草稿
{self.script}

## 配图 / 视频提示词
{self.image_prompt}

## 标签与 CTA
{', '.join(self.hashtags)}

{self.cta}

## 合规检查
{issues}
"""


class ContentWorkflow:
    def __init__(self) -> None:
        self.last_brief: ContentBrief | None = None

    def generate(self, topic: str, channel: str = "公众号", audience: str = "环保工程公司", tone: str = "专业、克制") -> ContentBrief:
        topic = (topic or "环保设备租赁如何选型").strip()
        channel = channel if channel in CHANNEL_TIPS else "公众号"
        titles = [template.format(topic=topic) for template in TITLE_TEMPLATES]
        hook = (
            f"很多{audience}在“{topic}”这件事上，先看价格，后看工况，结果设备到场才发现处理量、"
            "电源或场地不匹配。先把下面 3 个问题确认清楚，再谈报价，沟通成本会低很多。"
        )
        outline = [
            "先确认工况边界：处理对象、流量/风量、浓度、场地和排放标准。",
            "再把费用拆开：租金、押金、运输、安装、耗材、维保分别列项。",
            "最后写清验收与退出：验收标准、SLA、备用机、退租和押金退还条件。",
        ]
        script = self._build_script(topic, audience, channel)
        compliance = check_content(script)
        brief = ContentBrief(
            topic=topic,
            channel=channel,
            audience=audience,
            tone=tone,
            titles=titles,
            hook=hook,
            outline=outline,
            script=script,
            image_prompt=(
                "Clean editorial photo of an industrial environmental equipment site, "
                "engineer in safety vest checking a compact wastewater unit, natural light, "
                "documentary style, 35mm, no text, no logo, 16:9"
            ),
            hashtags=["#环保设备租赁", "#污水处理", "#EHS", "#环保验收", "#设备选型"],
            cta=f"如果你正在做“{topic}”，可以在评论区回复「清单」，领取一份选型与验收集成表。",
            compliance=compliance,
            status="ready_for_review" if compliance["passed"] else "needs_revision",
        )
        self.last_brief = brief
        return brief

    @staticmethod
    def _build_script(topic: str, audience: str, channel: str) -> str:
        channel_tip = CHANNEL_TIPS[channel]
        return f"""很多{audience}在“{topic}”这件事上，容易把注意力放在单日租金上，却忽略了工况、运输、安装和退租这些会影响总成本的因素。

先确认工况。把处理对象、设计流量或风量、入口浓度、现场电源和排放标准整理成一页纸。只告诉供应商“面积多大”或“设备要便宜”，通常无法得到准确的选型方案。

再把费用拆开。要求报价单至少列出设备租金、押金、运输、安装调试、耗材、维保和税费。长租折扣、备用机、二次移位、夜间施工是否另收费，也要提前写进合同附件。

最后写清验收和退出。验收用什么标准、多久内完成、故障多久响应、什么情况提供备用机、提前退租和押金退还原则，都应该在签约前确认。

{channel_tip}

本文为演示内容，不构成采购或法律建议；具体项目请以现场勘查和合同为准。"""


def run_content_workflow(topic: str, channel: str = "公众号", audience: str = "环保工程公司") -> dict:
    return ContentWorkflow().generate(topic, channel, audience).as_dict()
