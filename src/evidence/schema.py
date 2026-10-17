"""Compact evidence cards used by the incident investigator."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceCard:
    evidence_id: str
    source_type: str
    source: str
    service: str
    signal: str
    time_start: str | None
    time_end: str | None
    observation: str
    raw_reference: str
    extractor_version: str = "rule-v1"
    confidence: float = 1.0


@dataclass(frozen=True)
class InvestigationFinding:
    hypothesis: str | None
    status: str
    evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...] = ()
