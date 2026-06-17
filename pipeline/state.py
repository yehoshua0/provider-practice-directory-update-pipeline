from typing import Literal, TypedDict


class ProviderRecord(TypedDict):
    provider_id: str
    npi: str
    provider_name: str
    specialty: str
    practice_name: str
    address: str
    phone: str
    website: str
    active: bool | None
    last_verified_date: str  # ISO 8601 date string


class FieldDiff(TypedDict):
    field: str
    old_value: str
    new_value: str
    confidence_score: float
    supporting_sources: list[str]


class PipelineState(TypedDict):
    record: ProviderRecord
    raw_sources: dict[str, dict]            # source_name → raw payload; None if fetch failed
    normalized: dict[str, ProviderRecord]   # source_name → normalized record
    diffs: list[FieldDiff]
    overall_confidence: float
    recommended_action: Literal["auto_update", "human_review", "no_change"]
    reason: str
    error: str | None
