"""Shared paths and lightweight configuration."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
PROMPTS_DIR = ROOT / "prompts"

FAQ_PATH = DATA_DIR / "customer_service" / "faq.jsonl"
EVAL_PATH = DATA_DIR / "customer_service" / "eval_set.jsonl"
ORDERS_PATH = DATA_DIR / "customer_service" / "orders.json"
PRICING_PATH = DATA_DIR / "customer_service" / "pricing.json"
TOOLS_PATH = DATA_DIR / "customer_service" / "tool_schemas.json"

CONTENT_PERFORMANCE_PATH = DATA_DIR / "content" / "performance.csv"
CONTENT_CALENDAR_PATH = DATA_DIR / "content" / "calendar.csv"
PROCESS_PATH = DATA_DIR / "environment" / "process_steps.csv"
BID_DIR = DATA_DIR / "environment" / "bid_docs"


def ensure_reports() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR
