"""Bid-document extraction and retrieval for environmental projects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import BID_DIR
from ..text import clip, tokenize
from ..rag.bm25 import BM25


DATE_RE = re.compile(r"(20\d{2})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*日?")
MONEY_RE = re.compile(r"预算(?:金额)?[^0-9]{0,8}([0-9,]+(?:\.[0-9]+)?)\s*万元")
PROJECT_ID_RE = re.compile(r"项目编号[：:\s]*([A-Za-z0-9\-]+)")


@dataclass
class BidDocument:
    path: Path
    title: str
    text: str
    summary: dict[str, Any] = field(default_factory=dict)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；;])|\n+", text)
    cleaned: list[str] = []
    for part in parts:
        item = part.strip(" -\t")
        if not item or item.startswith("#") or item.startswith(">"):
            continue
        if "虚构" in item or "仅用于演示" in item:
            continue
        if len(item) >= 12:
            cleaned.append(clip(item, 220))
    return cleaned


def _pick(sentences: list[str], keywords: tuple[str, ...], limit: int = 6) -> list[str]:
    seen: set[str] = set()
    picked: list[str] = []
    for sentence in sentences:
        if any(k in sentence for k in keywords) and sentence not in seen:
            seen.add(sentence)
            picked.append(sentence)
        if len(picked) >= limit:
            break
    return picked


def _dates(text: str) -> list[dict[str, str]]:
    labels = (
        ("投标截止", ("投标截止", "递交截止", "投标文件递交")),
        ("开标", ("开标",)),
        ("答疑截止", ("答疑",)),
        ("现场踏勘", ("踏勘",)),
        ("服务开始", ("服务开始", "服务期开始")),
        ("交付", ("完成设备到货", "完成安装调试", "服务期")),
    )
    result: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        dates = DATE_RE.findall(line)
        if not dates:
            continue
        for label, keys in labels:
            if any(k in line for k in keys):
                for y, m, d in dates:
                    result.append({"label": label, "date": f"{int(y):04d}-{int(m):02d}-{int(d):02d}", "context": clip(line, 100)})
                break
    # Dedupe by label + date.
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in result:
        key = (item["label"], item["date"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _section_map(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "正文"
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return {key: "\n".join(value) for key, value in sections.items()}


def _section_text(sections: dict[str, str], *keywords: str) -> str:
    return "\n".join(text for heading, text in sections.items() if any(key in heading for key in keywords))


def summarize_bid(text: str, title: str | None = None) -> dict[str, Any]:
    sections = _section_map(text)
    all_sentences = _sentences(text)
    title = title or next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), "未命名招标文件")
    project_id = PROJECT_ID_RE.search(text)
    budget = MONEY_RE.search(text)

    def pick_section(*keywords: str, fallback_keywords: tuple[str, ...], limit: int) -> list[str]:
        section_text = _section_text(sections, *keywords)
        sentences = _sentences(section_text)
        if sentences:
            return _pick(sentences, fallback_keywords, limit)
        return _pick(all_sentences, fallback_keywords, limit)

    return {
        "title": title,
        "project_id": project_id.group(1) if project_id else None,
        "budget_wan": float(budget.group(1).replace(",", "")) if budget else None,
        "key_dates": _dates(text),
        "qualifications": pick_section(
            "资格", fallback_keywords=("资格", "资质", "须提供", "须具备", "ISO", "认证", "业绩", "不得被列入", "不接受联合体"), limit=8
        ),
        "technical_requirements": pick_section(
            "技术", fallback_keywords=("须", "不低于", "不大于", "支持", "执行"), limit=8
        ),
        "commercial_terms": pick_section(
            "商务", fallback_keywords=("保证金", "付款", "发票", "报价须", "履约"), limit=7
        ),
        "scoring": pick_section(
            "评标", "评分", fallback_keywords=("评分", "总分", "技术部分", "商务部分", "价格部分", "技术得分"), limit=6
        ),
        "risk_clauses": _pick(
            all_sentences, ("废标", "无效", "扣减", "解除合同", "赔偿", "处罚", "不得", "不允许"), 8
        ),
        "word_count": len(text),
        "synthetic": "合成招标文件" in text or "虚构" in text,
    }


def summarize_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    summary = summarize_bid(text, title=path.stem.replace("_", " "))
    summary["file"] = path.name
    return summary


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['title']}",
        "",
        f"- 项目编号：{summary.get('project_id') or '未识别'}",
        f"- 预算：{summary.get('budget_wan') or '未识别'} 万元",
        f"- 文件字数：{summary['word_count']}",
        f"- 数据类型：{'合成招标文件' if summary.get('synthetic') else '待确认'}",
        "",
        "## 关键日期",
        "",
        "| 节点 | 日期 | 原文 |",
        "| --- | --- | --- |",
    ]
    if summary["key_dates"]:
        for item in summary["key_dates"]:
            lines.append(f"| {item['label']} | {item['date']} | {item['context']} |")
    else:
        lines.append("| 未识别 | - | - |")
    sections = [
        ("资格要求", "qualifications"),
        ("技术需求", "technical_requirements"),
        ("商务条款", "commercial_terms"),
        ("评分办法", "scoring"),
        ("风险条款", "risk_clauses"),
    ]
    for heading, key in sections:
        lines.extend(["", f"## {heading}", ""])
        if summary[key]:
            lines.extend(f"- {item}" for item in summary[key])
        else:
            lines.append("- 未识别")
    lines.append("")
    return "\n".join(lines)


class BidAssistant:
    """Small retrieval + structured-answer layer over the bid documents."""

    KEY_TERMS = ("截止", "预算", "开标", "资格", "资质", "评分", "保证金", "付款", "发票", "服务期", "验收")

    def __init__(self, bid_dir: Path = BID_DIR):
        self.documents: list[BidDocument] = []
        for path in sorted(bid_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.documents.append(BidDocument(path=path, title=path.stem, text=text, summary=summarize_bid(text)))
        if not self.documents:
            raise ValueError(f"No bid documents found in {bid_dir}")
        self.index = BM25([tokenize(doc.text) for doc in self.documents])

    def _best_snippet(self, question: str, text: str) -> str:
        q_terms = set(tokenize(question))
        key_terms = {term for term in self.KEY_TERMS if term in question}

        def score(sentence: str) -> float:
            s_terms = set(tokenize(sentence))
            overlap = len(q_terms & s_terms)
            keyword_bonus = sum(6 for term in key_terms if term in sentence)
            return overlap * 2 + keyword_bonus

        return max(_sentences(text), key=score, default="")

    def search(self, question: str, top_k: int = 3) -> list[dict[str, Any]]:
        hits = self.index.search(tokenize(question), top_k=top_k)
        results = []
        for index, score in hits:
            doc = self.documents[index]
            best = self._best_snippet(question, doc.text)
            results.append(
                {
                    "file": doc.path.name,
                    "title": doc.summary["title"],
                    "score": round(score, 4),
                    "snippet": clip(best, 220),
                }
            )
        return results

    def _doc_by_file(self, filename: str) -> BidDocument | None:
        return next((doc for doc in self.documents if doc.path.name == filename), None)

    def _line(self, doc: BidDocument, *keywords: str) -> str:
        for line in doc.text.splitlines():
            item = line.strip(" -\t")
            if item and not item.startswith("#") and any(key in item for key in keywords):
                return clip(item, 220)
        return ""

    def _deadline(self, doc: BidDocument, label: str = "投标截止") -> dict[str, str] | None:
        return next((item for item in doc.summary["key_dates"] if item["label"] == label), None)

    def _structured_answer(self, question: str, doc: BidDocument) -> dict[str, Any] | None:
        parts: list[str] = []
        citations: list[dict[str, Any]] = []

        def clean(items: list[str]) -> list[str]:
            return [item.rstrip("。；; ") for item in items if item.strip()]

        if "预算" in question and doc.summary.get("budget_wan"):
            line = self._line(doc, "预算金额", "预算")
            parts.append(f"预算 {doc.summary['budget_wan']:g} 万元")
            if line:
                citations.append({"file": doc.path.name, "title": doc.summary["title"], "snippet": line})

        if "截止" in question:
            deadline = self._deadline(doc)
            if deadline:
                parts.append(f"投标截止 {deadline['date']}")
                citations.append({"file": doc.path.name, "title": doc.summary["title"], "snippet": deadline["context"]})

        if "开标" in question:
            opening = self._deadline(doc, "开标")
            if opening:
                parts.append(f"开标 {opening['date']}")
                citations.append({"file": doc.path.name, "title": doc.summary["title"], "snippet": opening["context"]})

        if ("资格" in question or "资质" in question) and doc.summary["qualifications"]:
            items = clean(doc.summary["qualifications"][:3])
            parts.append("资格要求包括：" + "；".join(items))
            citations.append({"file": doc.path.name, "title": doc.summary["title"], "snippet": "；".join(items)})

        if "评分" in question and doc.summary["scoring"]:
            items = clean(doc.summary["scoring"][:3])
            parts.append("评分办法：" + "；".join(items))
            citations.append({"file": doc.path.name, "title": doc.summary["title"], "snippet": "；".join(items)})

        if "保证金" in question and doc.summary["commercial_terms"]:
            item = next((x for x in doc.summary["commercial_terms"] if "保证金" in x), doc.summary["commercial_terms"][0])
            item = clean([item])[0]
            parts.append(item)
            citations.append({"file": doc.path.name, "title": doc.summary["title"], "snippet": item})

        if "服务期" in question or "工期" in question:
            service = self._deadline(doc, "服务开始")
            if service:
                parts.append(f"服务开始 {service['date']}")
                citations.append({"file": doc.path.name, "title": doc.summary["title"], "snippet": service["context"]})

        if not parts:
            return None
        return {
            "answer": f"《{doc.summary['title']}》：" + "；".join(parts) + "。",
            "citations": citations,
        }

    def answer(self, question: str) -> dict[str, Any]:
        hits = self.search(question, top_k=2)
        if not hits:
            return {"answer": "没有在招标文件中找到相关内容，建议换一个关键词或查看原文。", "citations": []}

        # Comparison questions: list all deadlines / budgets in order.
        if ("哪个" in question or "更早" in question or "最早" in question) and ("截止" in question or "预算" in question):
            rows = []
            for doc in self.documents:
                if "截止" in question:
                    deadline = self._deadline(doc)
                    if deadline:
                        rows.append((deadline["date"], doc, f"投标截止 {deadline['date']}", deadline["context"]))
                elif doc.summary.get("budget_wan"):
                    rows.append((str(doc.summary["budget_wan"]), doc, f"预算 {doc.summary['budget_wan']:g} 万元", self._line(doc, "预算")))
            if rows:
                rows.sort(key=lambda x: x[0])
                lines = ["按投标截止时间从早到晚："] if "截止" in question else ["按预算从低到高："]
                cites = []
                for _, doc, text, source in rows:
                    lines.append(f"- 《{doc.summary['title']}》{text}")
                    cites.append({"file": doc.path.name, "title": doc.summary["title"], "snippet": source})
                return {"answer": "\n".join(lines), "citations": cites}

        top_doc = self._doc_by_file(hits[0]["file"])
        if top_doc:
            structured = self._structured_answer(question, top_doc)
            if structured:
                return structured

        lines = [f"未直接命中结构化字段，以下是《{hits[0]['title']}》中可能相关的原文："]
        for hit in hits:
            lines.append(f"- {hit['snippet']}（{hit['file']}）")
        return {"answer": "\n".join(lines), "citations": hits}
