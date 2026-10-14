"""Small dependency-free TF-IDF index over runbook sections."""

from collections import Counter
from dataclasses import dataclass
from math import log, sqrt
from pathlib import Path
import re

TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = {"a", "an", "and", "are", "at", "be", "before", "by", "for",
             "from", "in", "is", "of", "on", "or", "the", "to", "with"}


def tokenize(text: str) -> list[str]:
    return [word for word in TOKEN.findall(text.casefold()) if word not in STOPWORDS]


@dataclass(frozen=True)
class Section:
    path: str
    heading: str
    text: str


@dataclass(frozen=True)
class SearchHit:
    section: Section
    score: float


def load_sections(directory: str | Path) -> list[Section]:
    root = Path(directory)
    sections = []
    for path in sorted(root.glob("*.md")):
        heading = ""
        body: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                if heading and body:
                    sections.append(Section(str(path), heading, "\n".join(body).strip()))
                heading, body = line[3:].strip(), []
            elif heading:
                body.append(line)
        if heading and body:
            sections.append(Section(str(path), heading, "\n".join(body).strip()))
    return sections


class TfidfIndex:
    def __init__(self, sections: list[Section]):
        self.sections = sections
        counts = [Counter(tokenize(f"{s.heading} {s.text}")) for s in sections]
        document_frequency = Counter(term for count in counts for term in count)
        self.idf = {term: log((1 + len(sections)) / (1 + frequency)) + 1
                    for term, frequency in document_frequency.items()}
        self.vectors = [self._vector(count) for count in counts]

    def _vector(self, counts: Counter) -> dict[str, float]:
        weights = {term: (1 + log(count)) * self.idf[term]
                   for term, count in counts.items() if term in self.idf}
        length = sqrt(sum(value * value for value in weights.values()))
        return {term: value / length for term, value in weights.items()} if length else {}

    def search(self, query: str, limit: int = 3) -> list[SearchHit]:
        if limit < 1:
            raise ValueError("limit must be positive")
        query_vector = self._vector(Counter(tokenize(query)))
        hits = []
        for section, vector in zip(self.sections, self.vectors):
            score = sum(weight * vector.get(term, 0.0)
                        for term, weight in query_vector.items())
            if score > 0:
                hits.append(SearchHit(section, score))
        return sorted(hits, key=lambda hit: (-hit.score, hit.section.path,
                                              hit.section.heading))[:limit]
