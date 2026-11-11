"""Typed models shared by the RAG agent and evaluator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Document:
    id: str
    group_id: str
    category: str
    question: str
    answer: str
    tags: tuple[str, ...] = ()
    source: str = "synthetic"
    synthetic: bool = True

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "Document":
        return cls(
            id=str(row["id"]),
            group_id=str(row.get("group_id") or row["id"]),
            category=str(row.get("category", "")),
            question=str(row.get("question", "")),
            answer=str(row.get("answer", "")),
            tags=tuple(row.get("tags", [])),
            source=str(row.get("source", "synthetic")),
            synthetic=bool(row.get("synthetic", True)),
        )


@dataclass(frozen=True)
class SearchHit:
    document: Document
    score: float
    snippet: str
    matched_terms: tuple[str, ...] = ()


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    latency_ms: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments,
            "result": self.result,
            "latency_ms": round(self.latency_ms, 3),
        }


@dataclass
class AgentResult:
    answer: str
    intent: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    confidence: float = 0.0
    handoff: bool = False
    handoff_ticket: str | None = None
    latency_ms: float = 0.0
    debug: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "intent": self.intent,
            "citations": self.citations,
            "tool_calls": [call.as_dict() for call in self.tool_calls],
            "confidence": self.confidence,
            "handoff": self.handoff,
            "handoff_ticket": self.handoff_ticket,
            "latency_ms": round(self.latency_ms, 3),
            "debug": self.debug,
        }
