"""A run-local store that only accepts source-linked evidence."""

from .schema import EvidenceCard


class EvidenceStore:
    def __init__(self, investigation_id: str):
        self.investigation_id = investigation_id
        self.cards: list[EvidenceCard] = []

    def add(self, *, source_type: str, source: str, service: str, signal: str,
            observation: str, raw_reference: str, time_start: str | None = None,
            time_end: str | None = None) -> EvidenceCard:
        if not source or not observation or not raw_reference:
            raise ValueError("Evidence requires a source, observation, and raw reference")
        card = EvidenceCard(f"ev-{len(self.cards) + 1:04d}", source_type, source,
                            service, signal, time_start, time_end, observation, raw_reference)
        self.cards.append(card)
        return card
