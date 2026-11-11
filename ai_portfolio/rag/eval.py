"""Offline retrieval and agent evaluation."""

from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from ..config import EVAL_PATH, REPORTS_DIR, ensure_reports
from ..text import tokenize
from .agent import CustomerServiceAgent
from .retriever import KnowledgeBase


def load_eval(path: Path = EVAL_PATH) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _unique_groups(docs: list[Any]) -> list[str]:
    groups: list[str] = []
    for doc in docs:
        group = doc.group_id
        if group not in groups:
            groups.append(group)
    return groups


def _first_relevant_rank(groups: list[str], expected: list[str]) -> int:
    for rank, group in enumerate(groups, start=1):
        if group in expected:
            return rank
    return 0


def _keyword_baseline(kb: KnowledgeBase, query: str, top_k: int = 3) -> list[str]:
    query_terms = set(tokenize(query))
    scored: list[tuple[float, int]] = []
    for index, doc in enumerate(kb.documents):
        doc_terms = set(tokenize(doc.question + doc.answer))
        overlap = len(query_terms & doc_terms)
        if overlap:
            scored.append((overlap / math.sqrt(max(1, len(doc_terms))), index))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return _unique_groups([kb.documents[i] for _, i in scored[: top_k * 4]])[:top_k]


def evaluate(kb: KnowledgeBase | None = None, agent: CustomerServiceAgent | None = None) -> dict[str, Any]:
    kb = kb or KnowledgeBase.from_jsonl()
    agent = agent or CustomerServiceAgent(kb)
    rows = load_eval()
    faq_rows = [r for r in rows if r.get("expected_groups")]

    hit1 = hit3 = 0
    reciprocal_ranks: list[float] = []
    baseline_hits = 0
    difficulty_stats: dict[str, dict[str, int]] = {
        "easy": {"total": 0, "hit": 0},
        "hard": {"total": 0, "hit": 0},
    }
    retrieval_cases: list[dict[str, Any]] = []
    for row in faq_rows:
        expected = row["expected_groups"]
        hits = kb.search(row["question"], top_k=3)
        groups = _unique_groups([hit.document for hit in hits])
        rank = _first_relevant_rank(groups, expected)
        difficulty = row.get("difficulty", "easy")
        difficulty_stats.setdefault(difficulty, {"total": 0, "hit": 0})
        difficulty_stats[difficulty]["total"] += 1
        if rank:
            difficulty_stats[difficulty]["hit"] += 1
        if rank == 1:
            hit1 += 1
        if rank:
            hit3 += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)
        baseline_groups = _keyword_baseline(kb, row["question"], top_k=3)
        baseline_rank = _first_relevant_rank(baseline_groups, expected)
        if baseline_rank:
            baseline_hits += 1
        retrieval_cases.append(
            {
                "id": row["id"],
                "question": row["question"],
                "difficulty": difficulty,
                "expected_groups": expected,
                "retrieved_groups": groups,
                "rank": rank,
                "baseline_groups": baseline_groups,
            }
        )

    intent_correct = tool_correct = citation_correct = handoff_correct = 0
    latencies: list[float] = []
    agent_cases: list[dict[str, Any]] = []
    for row in rows:
        result = agent.answer(row["question"])
        latencies.append(result.latency_ms)
        intent_ok = result.intent == row["expected_intent"]
        tool_names = [call.name for call in result.tool_calls]
        tool_ok = row["expected_tool"] in tool_names
        citation_groups = [c.get("group_id") for c in result.citations]
        citation_ok = (not row["expected_groups"]) or any(g in row["expected_groups"] for g in citation_groups)
        handoff_ok = (row["expected_intent"] != "handoff") or result.handoff
        intent_correct += int(intent_ok)
        tool_correct += int(tool_ok)
        citation_correct += int(citation_ok)
        handoff_correct += int(handoff_ok)
        agent_cases.append(
            {
                "id": row["id"],
                "question": row["question"],
                "expected_intent": row["expected_intent"],
                "actual_intent": result.intent,
                "expected_tool": row["expected_tool"],
                "tools": tool_names,
                "intent_ok": intent_ok,
                "tool_ok": tool_ok,
                "citation_ok": citation_ok,
                "handoff_ok": handoff_ok,
                "handoff": result.handoff,
                "confidence": result.confidence,
                "answer_preview": result.answer[:180],
            }
        )

    total = len(rows)
    faq_total = max(1, len(faq_rows))
    metrics = {
        "documents": len(kb),
        "eval_cases": total,
        "faq_cases": len(faq_rows),
        "retrieval_hit_at_1": round(hit1 / faq_total, 4),
        "retrieval_hit_at_3": round(hit3 / faq_total, 4),
        "retrieval_mrr": round(sum(reciprocal_ranks) / faq_total, 4),
        "easy_hit_at_3": round(
            difficulty_stats.get("easy", {}).get("hit", 0) / max(1, difficulty_stats.get("easy", {}).get("total", 0)), 4
        ),
        "hard_hit_at_3": round(
            difficulty_stats.get("hard", {}).get("hit", 0) / max(1, difficulty_stats.get("hard", {}).get("total", 0)), 4
        ),
        "keyword_baseline_hit_at_3": round(baseline_hits / faq_total, 4),
        "intent_accuracy": round(intent_correct / total, 4),
        "tool_accuracy": round(tool_correct / total, 4),
        "citation_hit_rate": round(citation_correct / total, 4),
        "handoff_accuracy": round(handoff_correct / total, 4),
        "avg_latency_ms": round(statistics.mean(latencies), 3) if latencies else 0.0,
    }
    return {"metrics": metrics, "retrieval_cases": retrieval_cases, "agent_cases": agent_cases}


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    m = report["metrics"]
    lines = [
        "# 检索与 Agent 评测报告",
        "",
        "> 由 `python -m ai_portfolio.cli eval` 自动生成。数据为合成数据，指标仅用于验证工程实现。",
        "",
        "## 总览",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 知识库文档数 | {m['documents']} |",
        f"| 评测用例数 | {m['eval_cases']}（FAQ {m['faq_cases']}） |",
        f"| Retrieval Hit@1 | {_pct(m['retrieval_hit_at_1'])} |",
        f"| Retrieval Hit@3 | {_pct(m['retrieval_hit_at_3'])} |",
        f"| Retrieval MRR | {m['retrieval_mrr']:.3f} |",
        f"| 简单子集 Hit@3 | {_pct(m['easy_hit_at_3'])} |",
        f"| 困难子集 Hit@3 | {_pct(m['hard_hit_at_3'])} |",
        f"| 关键词基线 Hit@3 | {_pct(m['keyword_baseline_hit_at_3'])} |",
        f"| 意图识别准确率 | {_pct(m['intent_accuracy'])} |",
        f"| 工具选择准确率 | {_pct(m['tool_accuracy'])} |",
        f"| 引用命中率 | {_pct(m['citation_hit_rate'])} |",
        f"| 转人工准确率 | {_pct(m['handoff_accuracy'])} |",
        f"| 平均响应时间 | {m['avg_latency_ms']:.2f} ms |",
        "",
        "## Agent 失败案例（含引用未命中）",
        "",
        "| 用例 | 期望意图 | 实际意图 | 期望工具 | 实际工具 | 引用命中 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    failures = [c for c in report["agent_cases"] if not (c["intent_ok"] and c["tool_ok"] and c["citation_ok"] and c["handoff_ok"])]
    if not failures:
        lines.append("| 无 | - | - | - | - | - |")
    else:
        for case in failures[:12]:
            lines.append(
                f"| {case['id']} | {case['expected_intent']} | {case['actual_intent']} | "
                f"{case['expected_tool']} | {', '.join(case['tools']) or '-'} | "
                f"{'是' if case['citation_ok'] else '否'} |"
            )
    lines.extend(
        [
            "",
            "## 检索未命中案例",
            "",
            "| 难度 | 问题 | 期望知识点 | 实际 Top3 |",
            "| --- | --- | --- | --- |",
        ]
    )
    retrieval_failures = [c for c in report["retrieval_cases"] if c["rank"] == 0]
    if not retrieval_failures:
        lines.append("| - | 无 | - | - |")
    else:
        for case in retrieval_failures:
            lines.append(
                f"| {case['difficulty']} | {case['question']} | {', '.join(case['expected_groups'])} | "
                f"{', '.join(case['retrieved_groups']) or '-'} |"
            )
    lines.extend(
        [
            "",
            "## 口径说明",
            "",
            "- Hit@k 按 `group_id` 去重，同一知识点的不同改写只计一次。",
            "- 简单子集使用 FAQ 同义改写；困难子集刻意避开关键词，例如“开票/发票”“被偷/丢失”。",
            "- 关键词基线使用字符 token 的重合度，不含 BM25 的长度归一化。",
            "- 工具准确率检查期望工具是否出现在 Agent 的 tool_calls 中。",
            "- 所有延迟为本机单次运行结果，不代表生产环境 SLA。",
            "",
        ]
    )
    return "\n".join(lines)


def save_report(report: dict[str, Any]) -> tuple[Path, Path]:
    ensure_reports()
    json_path = REPORTS_DIR / "eval_results.json"
    md_path = REPORTS_DIR / "eval_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    started = time.perf_counter()
    report = evaluate()
    json_path, md_path = save_report(report)
    m = report["metrics"]
    print(f"Documents: {m['documents']} | FAQ cases: {m['faq_cases']} | Cases: {m['eval_cases']}")
    print(f"Hit@1: {m['retrieval_hit_at_1']:.2%} | Hit@3: {m['retrieval_hit_at_3']:.2%} | MRR: {m['retrieval_mrr']:.3f}")
    print(f"Intent: {m['intent_accuracy']:.2%} | Tool: {m['tool_accuracy']:.2%} | Citation: {m['citation_hit_rate']:.2%}")
    print(f"Report: {json_path} / {md_path}")
    print(f"Elapsed: {time.perf_counter() - started:.2f}s")


if __name__ == "__main__":
    main()
