"""Lightweight content compliance and quality checks."""

from __future__ import annotations

import re

BANNED_WORDS = {
    "最好": ("高", "绝对化用语，建议改为具体条件"),
    "最佳": ("高", "绝对化用语，建议改为具体条件"),
    "最便宜": ("高", "价格比较不可验证，建议删除"),
    "最低价": ("高", "价格比较不可验证，建议删除"),
    "行业第一": ("高", "无法证明的排名，建议删除或补充来源"),
    "销量第一": ("高", "无法证明的排名，建议删除或补充来源"),
    "排名第一": ("高", "无法证明的排名，建议删除或补充来源"),
    "国家级": ("高", "资质/荣誉需可核验，建议改为具体证书名称"),
    "顶级": ("高", "绝对化用语，建议改为参数或案例"),
    "绝对": ("高", "绝对化承诺，建议改为条件性描述"),
    "100%": ("高", "绝对化承诺，建议改为实测数据范围"),
    "保证": ("高", "承诺性用语，建议改为服务目标或 SLA"),
    "零风险": ("高", "无法承诺，建议删除"),
    "包过": ("高", "验收结果不可承诺，建议删除"),
    "稳赚": ("高", "收益承诺，建议删除"),
    "永久": ("中", "期限不明确，建议改为具体年限"),
    "唯一": ("高", "排他性表述，建议删除"),
    "央视推荐": ("高", "需提供授权证明，建议删除"),
    "全网最低": ("高", "价格比较不可验证，建议删除"),
}

CLAIM_PATTERN = re.compile(
    r"[^。！？!?\n]{0,30}(?:\d+(?:\.\d+)?\s*(?:%|％|倍|万元|元|天|小时|个月|年)|保证|免费|终身|国家级|第一)[^。！？!?\n]{0,30}[。！？!?]?"
)


def check_content(text: str) -> dict:
    text = text or ""
    hits = []
    for word, (level, suggestion) in BANNED_WORDS.items():
        if word in text:
            hits.append({"word": word, "level": level, "suggestion": suggestion})

    claims = [m.group(0).strip() for m in CLAIM_PATTERN.finditer(text) if m.group(0).strip()]
    emoji_count = len(re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", text))
    exclamation_count = text.count("！") + text.count("!")
    paragraphs = [p for p in text.split("\n") if p.strip()]

    issues: list[str] = []
    high_risk = [h for h in hits if h["level"] == "高"]
    if high_risk:
        issues.append(f"存在 {len(high_risk)} 个高风险绝对化用语")
    if len(text) < 120:
        issues.append("正文偏短，建议补充场景、步骤或案例")
    if len(text) > 1200:
        issues.append("正文偏长，建议拆成系列内容")
    if exclamation_count > 3:
        issues.append("感叹号过多，品牌语气偏营销")
    if emoji_count > 6:
        issues.append("表情符号过多，建议控制在 6 个以内")

    score = 100
    score -= len(high_risk) * 18
    score -= len([h for h in hits if h["level"] == "中"]) * 8
    score -= max(0, len(issues) - len(high_risk)) * 5
    score = max(0, min(100, score))

    return {
        "score": score,
        "passed": score >= 80 and not high_risk,
        "sensitive_hits": hits,
        "numeric_or_promise_claims": claims[:12],
        "style": {
            "chars": len(text),
            "paragraphs": len(paragraphs),
            "emoji_count": emoji_count,
            "exclamation_count": exclamation_count,
        },
        "issues": issues,
        "suggestions": [h["suggestion"] for h in hits[:6]],
    }
