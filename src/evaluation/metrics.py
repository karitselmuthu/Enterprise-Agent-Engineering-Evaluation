"""Deterministic text metrics; lexical overlap is not factual correctness."""

from collections import Counter
import re


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def exact_match(answer: str, reference: str) -> float:
    return float(tokens(answer) == tokens(reference))


def token_f1(answer: str, reference: str) -> float:
    predicted, expected = Counter(tokens(answer)), Counter(tokens(reference))
    overlap = sum((predicted & expected).values())
    if not predicted or not expected or overlap == 0:
        return 0.0
    precision = overlap / sum(predicted.values())
    recall = overlap / sum(expected.values())
    return 2 * precision * recall / (precision + recall)


def required_term_recall(answer: str, required_terms: tuple[str, ...]) -> float:
    if not required_terms:
        return 1.0
    haystack = tokens(answer)
    return sum(any(haystack[i:i + len(needle)] == needle
                   for i in range(len(haystack) - len(needle) + 1))
               for needle in (tokens(term) for term in required_terms)) / len(required_terms)
