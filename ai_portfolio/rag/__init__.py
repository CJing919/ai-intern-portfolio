"""RAG customer-service agent package."""

from .agent import CustomerServiceAgent, answer, detect_intent
from .models import AgentResult, Document, SearchHit, ToolCall
from .retriever import KnowledgeBase
from .tools import ToolBox

__all__ = [
    "AgentResult",
    "CustomerServiceAgent",
    "Document",
    "KnowledgeBase",
    "SearchHit",
    "ToolBox",
    "ToolCall",
    "answer",
    "detect_intent",
]
