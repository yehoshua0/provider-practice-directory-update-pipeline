from pipeline.normalizers.address import normalize_address
from pipeline.normalizers.phone import normalize_phone
from pipeline.normalizers.name import normalize_name
from pipeline.state import PipelineState, ProviderRecord

_NORMALIZABLE_FIELDS = ["provider_name", "address", "phone", "specialty", "practice_name"]


def normalize_node(state: PipelineState) -> PipelineState:
    normalized: dict[str, ProviderRecord] = {}

    for source_name, raw in state["raw_sources"].items():
        if raw is None:
            continue

        normalized[source_name] = ProviderRecord(
            provider_id=state["record"]["provider_id"],
            npi=state["record"]["npi"],
            provider_name=normalize_name(raw.get("provider_name", "")),
            specialty=raw.get("specialty", "").title(),
            practice_name=normalize_name(raw.get("practice_name", "")),
            address=normalize_address(raw.get("address", "")),
            phone=normalize_phone(raw.get("phone", "")),
            website=raw.get("website", ""),
            active=raw.get("active"),
            last_verified_date=state["record"]["last_verified_date"],
        )

    return {**state, "normalized": normalized}
