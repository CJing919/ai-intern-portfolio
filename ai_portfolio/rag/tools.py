"""Tool implementations used by the customer-service agent.

The JSON schemas live in data/customer_service/tool_schemas.json so the same
contract can be reused by an OpenAI-compatible function-calling endpoint.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import ORDERS_PATH, PRICING_PATH, TOOLS_PATH
from .models import ToolCall
from .retriever import KnowledgeBase


class ToolError(ValueError):
    """Raised when a tool cannot satisfy a request."""


def _round_money(value: float) -> float:
    return round(value + 1e-9, 2)


@dataclass
class ToolBox:
    kb: KnowledgeBase
    orders_path: Path = ORDERS_PATH
    pricing_path: Path = PRICING_PATH
    schemas_path: Path = TOOLS_PATH
    _handoff_counter: int = 0
    _handoffs: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.pricing = json.loads(self.pricing_path.read_text(encoding="utf-8"))
        self.orders = {row["order_id"]: row for row in json.loads(self.orders_path.read_text(encoding="utf-8"))}
        self.schemas = json.loads(self.schemas_path.read_text(encoding="utf-8"))

    def schema(self, name: str) -> dict[str, Any] | None:
        return next((s for s in self.schemas if s["name"] == name), None)

    def _equipment(self, equipment_type: str) -> dict[str, Any]:
        text = (equipment_type or "").lower()
        equipment = self.pricing["equipment"]
        for item in equipment:
            names = [item["name"], *item.get("aliases", [])]
            if any(name.lower() in text or text in name.lower() for name in names):
                return item
        names = "、".join(item["name"] for item in equipment)
        raise ToolError(f"未识别设备类型，可选：{names}")

    def get_quote(self, equipment_type: str, quantity: int = 1, days: int = 1, distance_km: float = 30.0) -> dict[str, Any]:
        item = self._equipment(equipment_type)
        quantity = int(quantity)
        days = int(days)
        distance_km = float(distance_km)
        if not 1 <= quantity <= 200:
            raise ToolError("数量需在 1—200 之间")
        if not 1 <= days <= 3650:
            raise ToolError("租期需在 1—3650 天之间")
        if distance_km < 0:
            raise ToolError("运输距离不能为负数")

        rental = item["daily_rate"] * quantity * days
        discount_rate = 0.0
        for band in self.pricing["long_rental_discounts"]:
            if days >= band["min_days"]:
                discount_rate = band["discount"]
                break
        discount = rental * discount_rate
        setup = item["setup_fee"] * quantity
        free_km = self.pricing["free_distance_km"]
        delivery = self.pricing["delivery_base_fee"] + max(0.0, distance_km - free_km) * self.pricing["delivery_per_km"]
        subtotal = rental - discount + setup + delivery
        tax = subtotal * self.pricing["tax_rate"]
        deposit = item["deposit"] * quantity
        total = subtotal + tax

        return {
            "equipment_type": item["name"],
            "quantity": quantity,
            "days": days,
            "distance_km": round(distance_km, 1),
            "currency": "CNY",
            "line_items": {
                "rental": _round_money(rental),
                "long_rental_discount": _round_money(-discount),
                "setup_fee": _round_money(setup),
                "delivery_fee": _round_money(delivery),
                "subtotal": _round_money(subtotal),
                "tax_13_percent": _round_money(tax),
                "total_including_tax": _round_money(total),
                "refundable_deposit": _round_money(deposit),
                "total_due_at_signing": _round_money(total + deposit),
            },
            "assumptions": [
                "报价为演示数据，实际以合同和现场勘查为准。",
                "报价含一次基础安装调试和常规维保。",
                "押金在验收无损坏、无欠费后 7—10 个工作日退回。",
            ],
            "quote_id": f"Q-{datetime.now().strftime('%Y%m%d')}-{abs(hash((item['name'], quantity, days))) % 10000:04d}",
        }

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        order_id = (order_id or "").strip().upper()
        order = self.orders.get(order_id)
        if not order:
            matches = [oid for oid in self.orders if order_id and order_id[-4:] in oid]
            return {
                "found": False,
                "order_id": order_id,
                "message": "未找到该订单，请核对订单号。",
                "suggestions": matches[:3],
            }
        return {"found": True, **order}

    def create_handoff_ticket(self, reason: str, summary: str, priority: str = "P2") -> dict[str, Any]:
        self._handoff_counter += 1
        priority = priority if priority in {"P1", "P2", "P3"} else "P2"
        ticket_id = f"HO-{datetime.now().strftime('%Y%m%d')}-{self._handoff_counter:04d}"
        ticket = {
            "ticket_id": ticket_id,
            "reason": reason,
            "summary": summary,
            "priority": priority,
            "status": "open",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "sla": "P1 30 分钟响应" if priority == "P1" else "P2 2 小时响应",
        }
        self._handoffs.append(ticket)
        return ticket

    def search_knowledge_base(self, query: str, top_k: int = 3) -> dict[str, Any]:
        hits = self.kb.search(query, top_k=top_k)
        return {
            "hits": [
                {
                    "id": hit.document.id,
                    "group_id": hit.document.group_id,
                    "question": hit.document.question,
                    "answer": hit.document.answer,
                    "score": hit.score,
                    "category": hit.document.category,
                }
                for hit in hits
            ]
        }

    def dispatch(self, name: str, arguments: dict[str, Any]) -> ToolCall:
        started = time.perf_counter()
        try:
            if name == "search_knowledge_base":
                result = self.search_knowledge_base(**arguments)
            elif name == "get_quote":
                result = self.get_quote(**arguments)
            elif name == "get_order_status":
                result = self.get_order_status(**arguments)
            elif name == "create_handoff_ticket":
                result = self.create_handoff_ticket(**arguments)
            else:
                raise ToolError(f"未知工具：{name}")
        except TypeError as exc:
            result = {"error": f"参数不匹配：{exc}"}
        except ToolError as exc:
            result = {"error": str(exc)}
        latency = (time.perf_counter() - started) * 1000
        return ToolCall(name=name, arguments=arguments, result=result, latency_ms=latency)

    @property
    def handoffs(self) -> list[dict[str, Any]]:
        return list(self._handoffs)


def extract_order_id(text: str) -> str | None:
    match = re.search(r"\b(EQ\d{7})\b", text.upper())
    return match.group(1) if match else None
