"""A small, dependency-free BM25 implementation."""

from __future__ import annotations

import math
from collections import Counter


class BM25:
    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        if not corpus:
            raise ValueError("BM25 corpus must not be empty")
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.n_docs = len(corpus)
        self.doc_lengths = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_lengths) / self.n_docs
        self.term_freqs = [Counter(doc) for doc in corpus]
        doc_freq: Counter[str] = Counter()
        for freqs in self.term_freqs:
            doc_freq.update(freqs.keys())
        self.idf = {
            term: math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))
            for term, df in doc_freq.items()
        }

    def score(self, query_tokens: list[str], index: int) -> float:
        if not query_tokens:
            return 0.0
        freqs = self.term_freqs[index]
        dl = self.doc_lengths[index] or 1
        score = 0.0
        for term in query_tokens:
            tf = freqs.get(term, 0)
            if not tf:
                continue
            idf = self.idf.get(term, 0.0)
            denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    def search(self, query_tokens: list[str], top_k: int = 5) -> list[tuple[int, float]]:
        scored = [(i, self.score(query_tokens, i)) for i in range(self.n_docs)]
        scored = [item for item in scored if item[1] > 0]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:top_k]
