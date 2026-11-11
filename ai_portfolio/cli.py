"""Command-line entry points for the portfolio demos."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import BID_DIR, REPORTS_DIR, ensure_reports
from .content.analytics import ContentAnalytics
from .content.pipeline import ContentWorkflow
from .environment.bid import BidAssistant, render_markdown as render_bid, summarize_file
from .environment.process import analyze_process, render_markdown as render_process
from .rag.agent import CustomerServiceAgent
from .rag.eval import evaluate, save_report


def _print_json(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_agent(args: argparse.Namespace) -> None:
    result = CustomerServiceAgent().answer(args.question)
    _print_json(result.as_dict())


def cmd_eval(_: argparse.Namespace) -> None:
    report = evaluate()
    save_report(report)
    _print_json(report["metrics"])


def cmd_content(args: argparse.Namespace) -> None:
    brief = ContentWorkflow().generate(args.topic, args.channel, args.audience)
    ensure_reports()
    path = REPORTS_DIR / "content_brief.md"
    path.write_text(brief.to_markdown(), encoding="utf-8")
    print(brief.to_markdown())
    print(f"\nSaved: {path}")


def cmd_content_report(_: argparse.Namespace) -> None:
    analytics = ContentAnalytics()
    ensure_reports()
    path = REPORTS_DIR / "content_report.md"
    path.write_text(analytics.to_markdown(), encoding="utf-8")
    _print_json(analytics.summary())
    print(f"\nSaved: {path}")


def cmd_analytics_ask(args: argparse.Namespace) -> None:
    _print_json(ContentAnalytics().answer_question(args.question))


def cmd_bid(args: argparse.Namespace) -> None:
    path = Path(args.file)
    summary = summarize_file(path)
    ensure_reports()
    out = REPORTS_DIR / f"bid_summary_{path.stem}.md"
    out.write_text(render_bid(summary), encoding="utf-8")
    print(render_bid(summary))
    print(f"\nSaved: {out}")


def cmd_bid_ask(args: argparse.Namespace) -> None:
    _print_json(BidAssistant().answer(args.question))


def cmd_process(_: argparse.Namespace) -> None:
    result = analyze_process()
    ensure_reports()
    path = REPORTS_DIR / "process_opportunities.md"
    path.write_text(render_process(result), encoding="utf-8")
    print(render_process(result))
    print(f"\nSaved: {path}")


def cmd_demo(_: argparse.Namespace) -> None:
    from .demo import run_all

    run_all()


def cmd_serve(args: argparse.Namespace) -> None:
    from .web import serve

    serve(host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI product / Agent portfolio demos")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("agent", help="Ask the customer-service RAG agent")
    p.add_argument("--question", required=True)
    p.set_defaults(func=cmd_agent)

    p = sub.add_parser("eval", help="Run retrieval and agent evaluation")
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("content", help="Generate a content brief")
    p.add_argument("--topic", default="环保设备租赁如何选型")
    p.add_argument("--channel", default="公众号")
    p.add_argument("--audience", default="环保工程公司")
    p.set_defaults(func=cmd_content)

    p = sub.add_parser("content-report", help="Generate the content analytics report")
    p.set_defaults(func=cmd_content_report)

    p = sub.add_parser("analytics-ask", help="Ask a question about content performance")
    p.add_argument("--question", required=True)
    p.set_defaults(func=cmd_analytics_ask)

    p = sub.add_parser("bid", help="Summarize one bid document")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_bid)

    p = sub.add_parser("bid-ask", help="Search across bid documents")
    p.add_argument("--question", required=True)
    p.set_defaults(func=cmd_bid_ask)

    p = sub.add_parser("process", help="Rank automation opportunities")
    p.set_defaults(func=cmd_process)

    p = sub.add_parser("demo", help="Run all demos and write reports")
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("serve", help="Start the local web demo")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
