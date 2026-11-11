"""A deterministic, grounded customer-service agent.

The agent demonstrates the product mechanics that matter in the JD:
intent routing, tool selection, RAG citations, confidence thresholds and
human handoff. It does not require an LLM API key, so every result is
reproducible in CI.
"""

from __future__ import annotations

import re
import time
from typing import Any

from ..text import clip, parse_int, parse_quantity
from .models import AgentResult, SearchHit, ToolCall
from .retriever import KnowledgeBase
from .tools import ToolBox, ToolError, extract_order_id


HANDOFF_TERMS = ("投诉", "人工", "退款", "纠纷", "律师", "曝光", "差评", "经理", "没人处理", "一直故障")
ORDER_TERMS = ("订单", "物流", "进度", "到货", "查一下", "什么时候到")
QUOTE_TERMS = ("报价", "价格", "多少钱", "费用", "租金", "怎么收费", "预算")
FAQ_TOPIC_TERMS = (
    "发票", "税率", "支付", "付款", "押金", "合同", "流程", "租期", "续租", "退租",
    "维保", "故障", "验收", "补贴", "校准", "数据", "保险", "违约金", "培训",
    "耗材", "电源", "场地", "型号", "处理量", "运输", "运费", "包含", "包括",
)
DOMAIN_TERMS = (
    "设备", "租赁", "出租", "租用", "租金", "押金", "报价", "价格", "费用", "发票", "开票",
    "税率", "合同", "订单", "物流", "发货", "到货", "安装", "调试", "维保", "维修", "故障",
    "机器", "坏了", "师傅", "验收", "环保", "监测", "污水", "扬尘", "噪声", "除尘", "废气",
    "水质", "危废", "退租", "续租", "租期", "培训", "保险", "丢失", "被偷", "赔偿", "违约金",
    "逾期", "晚还", "归还", "备用机", "耗材", "平台", "数据", "补贴", "政策", "处理量",
    "教", "操作",
)
EQUIPMENT_HINTS = (
    "移动式污水处理设备", "污水处理设备", "污水设备", "扬尘监测设备", "扬尘监测",
    "噪声监测仪", "噪声", "工业除尘设备", "除尘设备", "废气处理设备", "废气",
    "水质在线监测仪", "水质监测", "危废暂存柜", "环保管家服务", "环保管家",
)


def detect_intent(text: str) -> str:
    if any(term in text for term in HANDOFF_TERMS):
        return "handoff"
    if extract_order_id(text) or any(term in text for term in ORDER_TERMS):
        return "order"

    has_quote_signal = any(term in text for term in QUOTE_TERMS)
    has_faq_topic = any(term in text for term in FAQ_TOPIC_TERMS)
    has_quantity = bool(re.search(r"(\d+|[一二两三四五六七八九十]+)\s*(台|套|个|件)", text))
    has_days = bool(re.search(r"(\d+|[一二两三四五六七八九十]+)\s*(天|个月|月)", text))
    if has_quote_signal and (has_quantity and has_days or "多少钱" in text or "报价多少" in text or "总费用" in text):
        return "quote"
    if has_faq_topic:
        return "faq"
    if has_quote_signal:
        return "quote"
    return "faq"



def _extract_days(text: str) -> int | None:
    month = re.search(r"(\d+|[一二两三四五六七八九十]+)\s*(?:个)?月", text)
    if month:
        value = parse_int(month.group(1))
        return value * 30 if value else None
    day = re.search(r"(\d+|[一二两三四五六七八九十]+)\s*天", text)
    if day:
        return parse_int(day.group(1))
    if "半年" in text:
        return 180
    if "一年" in text:
        return 365
    return None


def _extract_distance(text: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:公里|km|千米)", text, re.IGNORECASE)
    return float(match.group(1)) if match else 30.0


def _extract_equipment(text: str) -> str:
    # Prefer the longest alias so "移动式污水处理设备" wins over "污水设备".
    for hint in sorted(EQUIPMENT_HINTS, key=len, reverse=True):
        if hint in text:
            return hint
    return ""


def _citation(hit: SearchHit) -> dict[str, Any]:
    return {
        "id": hit.document.id,
        "group_id": hit.document.group_id,
        "question": hit.document.question,
        "category": hit.document.category,
        "score": hit.score,
        "source": hit.document.source,
    }


class CustomerServiceAgent:
    def __init__(self, kb: KnowledgeBase | None = None, toolbox: ToolBox | None = None, min_score: float = 1.0):
        self.kb = kb or KnowledgeBase.from_jsonl()
        self.toolbox = toolbox or ToolBox(self.kb)
        self.min_score = min_score

    def answer(self, question: str) -> AgentResult:
        started = time.perf_counter()
        question = (question or "").strip()
        if not question:
            return AgentResult(
                answer="请描述一下你想咨询的问题，例如设备租赁、报价、订单进度或售后故障。",
                intent="unknown",
                confidence=0.2,
                latency_ms=(time.perf_counter() - started) * 1000,
            )

        intent = detect_intent(question)
        if intent == "handoff":
            return self._handoff(question, started)
        if not any(term in question for term in DOMAIN_TERMS):
            result = self._handoff(
                question,
                started,
                reason="超出知识库范围",
                prefix="这个问题不在我的服务范围内，已为你转人工确认。",
            )
            result.intent = "unknown"
            return result
        if intent == "order":
            return self._order(question, started)
        if intent == "quote":
            return self._quote(question, started)
        return self._faq(question, started)

    def _faq(self, question: str, started: float) -> AgentResult:
        hits = self.kb.search(question, top_k=3)
        search_call = self.toolbox.dispatch("search_knowledge_base", {"query": question, "top_k": 3})
        if not hits or hits[0].score < self.min_score:
            result = self._handoff(
                question,
                started,
                reason="知识库未命中",
                prefix="这个问题我暂时没有足够把握回答，已为你转人工确认。",
            )
            result.intent = "faq"
            result.tool_calls.insert(0, search_call)
            result.debug["top_score"] = hits[0].score if hits else 0.0
            return result

        # Deduplicate by group so the answer is not three paraphrases of one fact.
        unique: list[SearchHit] = []
        seen: set[str] = set()
        for hit in hits:
            if hit.document.group_id not in seen:
                seen.add(hit.document.group_id)
                unique.append(hit)

        top = unique[0]
        related = "、".join(hit.document.question for hit in unique[1:3])
        answer = top.document.answer
        if related:
            answer += f"\n\n你可能还想了解：{related}"
        answer += "\n\n以上为演示知识库内容，实际以合同和现场勘查为准。"

        confidence = min(0.95, 0.55 + min(top.score, 20.0) / 40.0)
        return AgentResult(
            answer=answer,
            intent="faq",
            citations=[_citation(hit) for hit in unique[:2]],
            tool_calls=[search_call],
            confidence=round(confidence, 2),
            latency_ms=(time.perf_counter() - started) * 1000,
            debug={"top_score": top.score, "matched_terms": list(top.matched_terms)},
        )

    def _quote(self, question: str, started: float) -> AgentResult:
        equipment = _extract_equipment(question)
        if not equipment:
            return AgentResult(
                answer="可以报价。请告诉我设备类型、数量、租期和项目所在地（或运输距离），例如：2 台移动式污水处理设备租 10 天。",
                intent="quote",
                confidence=0.55,
                latency_ms=(time.perf_counter() - started) * 1000,
            )

        quantity = parse_quantity(question, default=1)
        days = _extract_days(question) or 1
        distance = _extract_distance(question)
        args = {"equipment_type": equipment, "quantity": quantity, "days": days, "distance_km": distance}
        quote_call = self.toolbox.dispatch("get_quote", args)
        kb_call = self.toolbox.dispatch("search_knowledge_base", {"query": "报价包含哪些费用", "top_k": 1})

        result = quote_call.result
        if "error" in result:
            return AgentResult(
                answer=f"{result['error']}。请补充设备类型、数量、租期和运输距离，我再帮你核算。",
                intent="quote",
                tool_calls=[quote_call],
                confidence=0.45,
                latency_ms=(time.perf_counter() - started) * 1000,
            )

        items = result["line_items"]
        assumptions = "\n".join(f"- {item}" for item in result["assumptions"])
        answer = (
            f"按当前配置估算：{result['equipment_type']} {result['quantity']} 台 × {result['days']} 天，"
            f"运输距离 {result['distance_km']} 公里。\n"
            f"设备租金 {items['rental']:,.2f} 元，长租优惠 {items['long_rental_discount']:,.2f} 元，"
            f"安装调试 {items['setup_fee']:,.2f} 元，运输 {items['delivery_fee']:,.2f} 元，"
            f"增值税 {items['tax_13_percent']:,.2f} 元。\n"
            f"含税合计 {items['total_including_tax']:,.2f} 元；押金 {items['refundable_deposit']:,.2f} 元（可退），"
            f"签约时合计应付 {items['total_due_at_signing']:,.2f} 元。\n"
            f"说明：\n{assumptions}"
        )
        citations = []
        if kb_call.result.get("hits"):
            hit = kb_call.result["hits"][0]
            citations.append(
                {
                    "id": hit["id"],
                    "group_id": hit["group_id"],
                    "question": hit["question"],
                    "category": hit["category"],
                    "score": hit["score"],
                    "source": "synthetic-faq-v1",
                }
            )
        return AgentResult(
            answer=answer,
            intent="quote",
            citations=citations,
            tool_calls=[quote_call, kb_call],
            confidence=0.9,
            latency_ms=(time.perf_counter() - started) * 1000,
            debug={"quote_id": result["quote_id"]},
        )

    def _order(self, question: str, started: float) -> AgentResult:
        order_id = extract_order_id(question)
        if not order_id:
            return AgentResult(
                answer="请提供 9 位订单号（例如 EQ2026003），我帮你查询当前节点和预计时间。",
                intent="order",
                confidence=0.5,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        call = self.toolbox.dispatch("get_order_status", {"order_id": order_id})
        result = call.result
        if not result.get("found"):
            return AgentResult(
                answer=f"没有查到订单 {order_id}，请核对订单号，或转人工帮你进一步查询。",
                intent="order",
                tool_calls=[call],
                confidence=0.35,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        answer = (
            f"订单 {result['order_id']}（{result['customer']}）当前状态：{result['status']}。\n"
            f"当前节点：{result['current_step']}；预计：{result['eta']}；负责人：{result['owner']}。\n"
            f"备注：{result['note']}"
        )
        return AgentResult(
            answer=answer,
            intent="order",
            tool_calls=[call],
            confidence=0.95,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    def _handoff(
        self,
        question: str,
        started: float,
        reason: str | None = None,
        prefix: str | None = None,
    ) -> AgentResult:
        reason = reason or ("投诉/纠纷" if any(t in question for t in ("投诉", "纠纷", "退款", "律师", "曝光")) else "用户要求人工")
        priority = "P1" if any(t in question for t in ("投诉", "曝光", "律师", "安全", "纠纷")) else "P2"
        call = self.toolbox.dispatch(
            "create_handoff_ticket",
            {"reason": reason, "summary": clip(question, 120), "priority": priority},
        )
        ticket = call.result
        text = prefix or "已为你转接人工客服。"
        answer = (
            f"{text}\n"
            f"工单号：{ticket['ticket_id']}；优先级：{ticket['priority']}；{ticket['sla']}。\n"
            "人工同事会按工单顺序联系你，请保持电话畅通。"
        )
        return AgentResult(
            answer=answer,
            intent="handoff",
            tool_calls=[call],
            confidence=0.99,
            handoff=True,
            handoff_ticket=ticket["ticket_id"],
            latency_ms=(time.perf_counter() - started) * 1000,
            debug={"reason": reason, "priority": priority},
        )


def answer(question: str, agent: CustomerServiceAgent | None = None) -> dict[str, Any]:
    return (agent or CustomerServiceAgent()).answer(question).as_dict()
