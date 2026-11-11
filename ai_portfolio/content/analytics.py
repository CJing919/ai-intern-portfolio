"""Content performance analytics and a small natural-language query layer."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from ..config import CONTENT_PERFORMANCE_PATH


class ContentAnalytics:
    def __init__(self, path: Path = CONTENT_PERFORMANCE_PATH):
        self.path = path
        self.rows = self._load(path)

    @staticmethod
    def _load(path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    {
                        **row,
                        "views": int(row["views"]),
                        "likes": int(row["likes"]),
                        "comments": int(row["comments"]),
                        "shares": int(row["shares"]),
                        "leads": int(row["leads"]),
                        "spend": float(row["spend"]),
                    }
                )
        return rows

    def _totals(self, rows: list[dict[str, Any]]) -> dict[str, float]:
        views = sum(r["views"] for r in rows)
        interactions = sum(r["likes"] + r["comments"] + r["shares"] for r in rows)
        leads = sum(r["leads"] for r in rows)
        spend = sum(r["spend"] for r in rows)
        return {
            "posts": len(rows),
            "views": views,
            "interactions": interactions,
            "leads": leads,
            "spend": round(spend, 2),
            "engagement_rate": round(interactions / views, 4) if views else 0.0,
            "lead_conversion": round(leads / views, 4) if views else 0.0,
            "cpl": round(spend / leads, 2) if leads else 0.0,
            "avg_views_per_post": round(views / len(rows), 1) if rows else 0.0,
        }

    def by_channel(self) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in self.rows:
            grouped[row["channel"]].append(row)
        result = []
        for channel, rows in grouped.items():
            totals = self._totals(rows)
            result.append({"channel": channel, **totals})
        return sorted(result, key=lambda x: (-x["leads"], x["cpl"]))

    def by_week(self) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in self.rows:
            d = date.fromisoformat(row["date"])
            year, week, _ = d.isocalendar()
            grouped[f"{year}-W{week:02d}"].append(row)
        result = []
        for label in sorted(grouped):
            result.append({"week": label, **self._totals(grouped[label])})
        return result

    def top_topics(self, limit: int = 5) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in self.rows:
            grouped[row["topic"]].append(row)
        result = []
        for topic, rows in grouped.items():
            totals = self._totals(rows)
            result.append({"topic": topic, **totals})
        return sorted(result, key=lambda x: (-x["leads"], -x["views"]))[:limit]

    def summary(self) -> dict[str, Any]:
        totals = self._totals(self.rows)
        channels = self.by_channel()
        weeks = self.by_week()
        wow = None
        if len(weeks) >= 2:
            current, previous = weeks[-1]["leads"], weeks[-2]["leads"]
            wow = round((current - previous) / previous, 4) if previous else None
        return {
            **totals,
            "date_range": [min(r["date"] for r in self.rows), max(r["date"] for r in self.rows)],
            "best_channel_by_leads": channels[0]["channel"],
            "best_channel_by_cpl": min(channels, key=lambda x: x["cpl"])["channel"],
            "week_over_week_leads": wow,
            "by_channel": channels,
            "by_week": weeks,
            "top_topics": self.top_topics(5),
        }

    def answer_question(self, question: str) -> dict[str, Any]:
        q = (question or "").lower()
        summary = self.summary()
        channels = summary["by_channel"]
        if any(k in q for k in ("渠道", "平台")) and any(k in q for k in ("线索", "获客", "leads")):
            best = channels[0]
            return {
                "answer": f"{best['channel']} 的线索最多，共 {best['leads']} 条；CPL 为 {best['cpl']:.2f} 元。",
                "data": best,
            }
        if any(k in q for k in ("转化", "conversion")):
            best = max(channels, key=lambda x: x["lead_conversion"])
            return {
                "answer": (
                    f"整体线索转化率为 {summary['lead_conversion']:.2%}；"
                    f"转化率最高的渠道是 {best['channel']}（{best['lead_conversion']:.2%}）。"
                ),
                "data": {"overall": summary["lead_conversion"], "by_channel": channels},
            }
        if any(k in q for k in ("成本", "cpl", "获客成本")):
            best = min(channels, key=lambda x: x["cpl"])
            return {
                "answer": f"整体 CPL 为 {summary['cpl']:.2f} 元；CPL 最低的渠道是 {best['channel']}（{best['cpl']:.2f} 元）。",
                "data": {"overall": summary["cpl"], "by_channel": channels},
            }
        if any(k in q for k in ("周", "趋势", "环比", "week")):
            wow = summary["week_over_week_leads"]
            direction = "上升" if wow and wow > 0 else "下降" if wow and wow < 0 else "持平"
            return {
                "answer": f"最近一周线索环比{direction} {abs(wow or 0):.2%}。",
                "data": summary["by_week"],
            }
        if any(k in q for k in ("选题", "内容", "topic")):
            top = summary["top_topics"][0]
            return {
                "answer": f"线索贡献最高的选题是「{top['topic']}」，带来 {top['leads']} 条线索、{top['views']} 次曝光。",
                "data": summary["top_topics"],
            }
        return {
            "answer": (
                f"统计周期 {summary['date_range'][0]} 至 {summary['date_range'][1]}，"
                f"共 {summary['posts']} 条内容、{summary['views']} 次曝光、{summary['leads']} 条线索；"
                f"整体互动率 {summary['engagement_rate']:.2%}，CPL {summary['cpl']:.2f} 元。"
            ),
            "data": summary,
        }

    def to_markdown(self) -> str:
        s = self.summary()
        wow = s["week_over_week_leads"]
        lines = [
            "# 内容运营数据报告",
            "",
            "> 由 `python -m ai_portfolio.cli content-report` 自动生成。数据为合成数据。",
            "",
            "## 总览",
            "",
            "| 指标 | 数值 |",
            "| --- | ---: |",
            f"| 统计周期 | {s['date_range'][0]} 至 {s['date_range'][1]} |",
            f"| 内容条数 | {s['posts']} |",
            f"| 曝光量 | {s['views']:,} |",
            f"| 互动量 | {s['interactions']:,} |",
            f"| 线索数 | {s['leads']:,} |",
            f"| 互动率 | {s['engagement_rate']:.2%} |",
            f"| 线索转化率 | {s['lead_conversion']:.2%} |",
            f"| CPL | {s['cpl']:.2f} 元 |",
            f"| 周线索环比 | {wow:.2%} |" if wow is not None else "| 周线索环比 | - |",
            "",
            "## 渠道对比",
            "",
            "| 渠道 | 曝光 | 线索 | 转化率 | CPL |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for c in s["by_channel"]:
            lines.append(
                f"| {c['channel']} | {c['views']:,} | {c['leads']} | {c['lead_conversion']:.2%} | {c['cpl']:.2f} |"
            )
        lines.extend(
            [
                "",
                "## 选题 Top 5",
                "",
                "| 选题 | 曝光 | 线索 |",
                "| --- | ---: | ---: |",
            ]
        )
        for t in s["top_topics"]:
            lines.append(f"| {t['topic']} | {t['views']:,} | {t['leads']} |")
        lines.extend(
            [
                "",
                "## 结论",
                "",
                f"- 线索最多的渠道：{s['best_channel_by_leads']}。",
                f"- CPL 最低的渠道：{s['best_channel_by_cpl']}。",
                "- 建议把高线索选题拆成系列，并给低 CPL 渠道增加 10%—20% 预算做对照测试。",
                "",
            ]
        )
        return "\n".join(lines)


def analyze_performance() -> dict[str, Any]:
    return ContentAnalytics().summary()
