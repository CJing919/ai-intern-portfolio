"""Process mining / opportunity prioritisation for environmental operations."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ..config import PROCESS_PATH


def load_process_steps(path: Path = PROCESS_PATH) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    **row,
                    "avg_minutes": float(row["avg_minutes"]),
                    "monthly_volume": int(row["monthly_volume"]),
                    "automation_potential": float(row["automation_potential"]),
                    "risk": int(row["risk"]),
                    "data_ready": float(row["data_ready"]),
                }
            )
    return rows


def analyze_process(path: Path = PROCESS_PATH, top_n: int = 6) -> dict[str, Any]:
    rows = load_process_steps(path)
    for row in rows:
        monthly_hours = row["avg_minutes"] * row["monthly_volume"] / 60
        automatable_hours = monthly_hours * row["automation_potential"]
        saving_hours = automatable_hours * 0.6  # conservative realisation rate
        row["monthly_hours"] = round(monthly_hours, 1)
        row["automatable_hours"] = round(automatable_hours, 1)
        row["estimated_saving_hours"] = round(saving_hours, 1)
        row["priority_score"] = round(
            monthly_hours * row["automation_potential"] * row["data_ready"] / max(1, row["risk"]),
            2,
        )

    ranked = sorted(rows, key=lambda x: (-x["priority_score"], x["step_id"]))
    total_hours = sum(r["monthly_hours"] for r in rows)
    total_automatable = sum(r["automatable_hours"] for r in rows)
    total_saving = sum(r["estimated_saving_hours"] for r in rows)
    flows = sorted({r["flow"] for r in rows})
    by_flow = []
    for flow in flows:
        subset = [r for r in rows if r["flow"] == flow]
        by_flow.append(
            {
                "flow": flow,
                "steps": len(subset),
                "monthly_hours": round(sum(r["monthly_hours"] for r in subset), 1),
                "automatable_hours": round(sum(r["automatable_hours"] for r in subset), 1),
                "top_step": max(subset, key=lambda x: x["priority_score"])["step"],
            }
        )
    return {
        "steps": len(rows),
        "flows": by_flow,
        "total_monthly_hours": round(total_hours, 1),
        "total_automatable_hours": round(total_automatable, 1),
        "estimated_monthly_saving_hours": round(total_saving, 1),
        "estimated_annual_saving_hours": round(total_saving * 12, 1),
        "top_opportunities": ranked[:top_n],
        "all_steps": ranked,
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 业务流程 AI 自动化机会矩阵",
        "",
        "> 由 `python -m ai_portfolio.cli process` 自动生成。工时与访谈数据为合成数据。",
        "",
        "## 总览",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
        f"| 流程数 | {len(result['flows'])} |",
        f"| 流程节点数 | {result['steps']} |",
        f"| 当前月工时 | {result['total_monthly_hours']:.1f} 小时 |",
        f"| 可自动化月工时 | {result['total_automatable_hours']:.1f} 小时 |",
        f"| 预计月节省工时 | {result['estimated_monthly_saving_hours']:.1f} 小时 |",
        f"| 预计年节省工时 | {result['estimated_annual_saving_hours']:.1f} 小时 |",
        "",
        "## 流程分布",
        "",
        "| 流程 | 节点数 | 月工时 | 可自动化工时 | 优先级最高节点 |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for flow in result["flows"]:
        lines.append(
            f"| {flow['flow']} | {flow['steps']} | {flow['monthly_hours']:.1f} | "
            f"{flow['automatable_hours']:.1f} | {flow['top_step']} |"
        )
    lines.extend(
        [
            "",
            "## Top 6 机会点",
            "",
            "| 排名 | 节点 | 流程 | 月工时 | 自动化潜力 | 风险 | 优先级分 |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for rank, row in enumerate(result["top_opportunities"], start=1):
        lines.append(
            f"| {rank} | {row['step']} | {row['flow']} | {row['monthly_hours']:.1f} | "
            f"{row['automation_potential']:.0%} | {row['risk']} | {row['priority_score']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## 评分口径",
            "",
            "`优先级分 = 月工时 × 自动化潜力 × 数据就绪度 / 风险等级`。",
            "预计节省工时按 60% 的保守实现率估算，用于排期排序，不构成收益承诺。",
            "",
            "## 落地建议",
            "",
            "- 先做数据就绪度高、风险低的节点，例如日报取数、内容发布、发货跟踪。",
            "- 投诉、合同用印等高风险节点先做“AI 辅助 + 人工复核”，不要直接自动化。",
            "- 每个节点上线前定义基线工时、准确率和人工接管率，按月复盘。",
            "",
        ]
    )
    return "\n".join(lines)
