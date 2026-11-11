"""Run every demo once and write the evidence package to reports/."""

from __future__ import annotations

import json
from datetime import datetime

from .config import BID_DIR, REPORTS_DIR, ensure_reports
from .content.analytics import ContentAnalytics
from .content.pipeline import ContentWorkflow
from .environment.bid import render_markdown as render_bid, summarize_file
from .environment.process import analyze_process, render_markdown as render_process
from .rag.eval import evaluate, save_report


def run_all() -> dict:
    ensure_reports()
    eval_report = evaluate()
    save_report(eval_report)

    brief = ContentWorkflow().generate("污水设备租赁的 5 个成本坑", "公众号", "制造企业 EHS")
    (REPORTS_DIR / "content_brief.md").write_text(brief.to_markdown(), encoding="utf-8")

    analytics = ContentAnalytics()
    (REPORTS_DIR / "content_report.md").write_text(analytics.to_markdown(), encoding="utf-8")

    process = analyze_process()
    (REPORTS_DIR / "process_opportunities.md").write_text(render_process(process), encoding="utf-8")

    bid_sections = []
    for path in sorted(BID_DIR.glob("*.md")):
        summary = summarize_file(path)
        bid_sections.append(render_bid(summary))
    (REPORTS_DIR / "bid_summary.md").write_text("\n\n---\n\n".join(bid_sections), encoding="utf-8")

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "eval": eval_report["metrics"],
        "content": {
            "posts": analytics.summary()["posts"],
            "views": analytics.summary()["views"],
            "leads": analytics.summary()["leads"],
            "cpl": analytics.summary()["cpl"],
            "brief_status": brief.status,
            "brief_compliance_score": brief.compliance["score"],
        },
        "process": {
            "flows": len(process["flows"]),
            "steps": process["steps"],
            "monthly_hours": process["total_monthly_hours"],
            "automatable_hours": process["total_automatable_hours"],
            "annual_saving_hours": process["estimated_annual_saving_hours"],
        },
        "bid_documents": len(bid_sections),
    }
    (REPORTS_DIR / "portfolio_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    index = [
        "# 证据包索引",
        "",
        "由 `python -m ai_portfolio.cli demo` 生成。",
        "",
        "| 文件 | 内容 |",
        "| --- | --- |",
        "| [eval_report.md](eval_report.md) | 检索 / 意图 / 工具 / 引用评测 |",
        "| [content_brief.md](content_brief.md) | 内容生产工作流产出 |",
        "| [content_report.md](content_report.md) | 内容数据分析 |",
        "| [process_opportunities.md](process_opportunities.md) | 流程自动化机会矩阵 |",
        "| [bid_summary.md](bid_summary.md) | 三份招标文件结构化摘要 |",
        "| [portfolio_summary.json](portfolio_summary.json) | 机器可读指标汇总 |",
        "",
    ]
    (REPORTS_DIR / "README.md").write_text("\n".join(index), encoding="utf-8")

    print("Reports written to", REPORTS_DIR)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary
