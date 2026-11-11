"""Knowledge-base loading and retrieval."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import FAQ_PATH
from ..text import clip, tokenize
from .bm25 import BM25
from .models import Document, SearchHit


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class KnowledgeBase:
    def __init__(self, documents: list[Document]):
        if not documents:
            raise ValueError("Knowledge base is empty")
        self.documents = documents
        self._index = BM25([self._index_text(doc) for doc in documents])

    @staticmethod
    def _index_text(doc: Document) -> list[str]:
        # Index the question twice so that short queries match the intent.
        return tokenize(" ".join([doc.question, doc.question, doc.answer, doc.category, " ".join(doc.tags)]))

    @classmethod
    def from_jsonl(cls, path: Path = FAQ_PATH) -> "KnowledgeBase":
        return cls([Document.from_dict(row) for row in load_jsonl(path)])

    def search(self, query: str, top_k: int = 3) -> list[SearchHit]:
        query_tokens = list(dict.fromkeys(tokenize(query)))
        hits: list[SearchHit] = []
        for index, score in self._index.search(query_tokens, top_k=top_k):
            doc = self.documents[index]
            matched = tuple(t for t in query_tokens if t in self._index.term_freqs[index])[:8]
            hits.append(
                SearchHit(
                    document=doc,
                    score=round(score, 4),
                    snippet=clip(doc.answer, 180),
                    matched_terms=matched,
                )
            )
        return hits

    def get(self, doc_id: str) -> Document | None:
        return next((doc for doc in self.documents if doc.id == doc_id), None)

    def __len__(self) -> int:
        return len(self.documents)
