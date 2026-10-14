"""Runbook retrieval entry point."""

from pathlib import Path

from .index import SearchHit, TfidfIndex, load_sections

DEFAULT_KNOWLEDGE_BASE = Path(__file__).resolve().parents[2] / "data" / "knowledge_base"


class RunbookRetriever:
    def __init__(self, directory: str | Path = DEFAULT_KNOWLEDGE_BASE):
        self.index = TfidfIndex(load_sections(directory))

    def search(self, query: str, limit: int = 3) -> list[SearchHit]:
        return self.index.search(query, limit)
