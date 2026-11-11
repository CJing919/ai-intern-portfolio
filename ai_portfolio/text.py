"""Chinese-friendly text normalization and tokenization.

The demo deliberately avoids a heavyweight tokenizer so it can run with the
Python standard library only. Chinese text is indexed with character unigrams
and bigrams, which works well for short FAQ retrieval and keeps the project
reproducible on a fresh machine.
"""

from __future__ import annotations

import re

_CJK = r"\u4e00-\u9fff"
_TOKEN_RE = re.compile(rf"[{_CJK}]+|[a-zA-Z0-9]+(?:[.\-_/][a-zA-Z0-9]+)*")
_SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?")

STOPWORDS = {
    "的", "了", "是", "吗", "呢", "啊", "呀", "吧", "和", "与", "及", "或",
    "在", "有", "我", "你", "他", "她", "它", "们", "这", "那", "哪", "什么",
    "怎么", "如何", "多少", "可以", "需要", "请问", "想", "了解", "一下",
    "the", "a", "an", "is", "are", "to", "of", "and", "or", "for", "in",
}


def normalize(text: str) -> str:
    text = (text or "").strip().lower()
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("，", ",").replace("。", ".").replace("；", ";")
    text = text.replace("：", ":").replace("！", "!").replace("？", "?")
    return re.sub(r"\s+", " ", text)


def tokenize(text: str) -> list[str]:
    """Return Chinese unigrams/bigrams plus Latin words and numbers."""
    tokens: list[str] = []
    for chunk in _TOKEN_RE.findall(normalize(text)):
        if re.fullmatch(rf"[{_CJK}]+", chunk):
            chars = [c for c in chunk if c not in STOPWORDS]
            tokens.extend(chars)
            tokens.extend(chunk[i : i + 2] for i in range(len(chunk) - 1))
        else:
            token = chunk.lower()
            if token not in STOPWORDS:
                tokens.append(token)
    return [t for t in tokens if t]


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.findall(text or "") if s.strip()]


def clip(text: str, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text if len(text) <= limit else text[: limit - 1] + "…"


_CN_DIGITS = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def parse_int(value: str, default: int | None = None) -> int | None:
    """Parse '12', '十二', '三十' or '两' into an integer."""
    value = (value or "").strip()
    if not value:
        return default
    if value.isdigit():
        return int(value)
    if value in _CN_DIGITS:
        return _CN_DIGITS[value]
    if "十" in value:
        left, _, right = value.partition("十")
        tens = _CN_DIGITS.get(left, 1) if left else 1
        ones = _CN_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    return default


def parse_quantity(text: str, default: int = 1) -> int:
    match = re.search(r"(\d+)\s*(台|套|个|件|点位|公里|天|个月|月)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"([一二两三四五六七八九十]+)\s*(台|套|个|件|点位|公里|天|个月|月)", text)
    if match:
        return parse_int(match.group(1), default) or default
    return default
