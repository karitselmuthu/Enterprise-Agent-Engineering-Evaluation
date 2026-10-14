"""Future embedding adapters can implement this interface."""

from typing import Protocol


class EmbeddingModel(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
