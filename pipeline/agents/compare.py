from pipeline.state import FieldDiff, PipelineState

_COMPARED_FIELDS = ["provider_name", "specialty", "practice_name", "address", "phone", "active"]


def compare_node(state: PipelineState) -> PipelineState:
    record = state["record"]
    normalized = state["normalized"]

    if not normalized:
        return {**state, "diffs": []}

    # Collect each source's value per field
    diffs: list[FieldDiff] = []

    for field in _COMPARED_FIELDS:
        old_value = str(record.get(field, ""))
        values_by_source: dict[str, str] = {}

        for source_name, norm_record in normalized.items():
            val = norm_record.get(field)
            if val is None:
                continue
            new_val = str(val)
            if new_val:
                values_by_source[source_name] = new_val

        if not values_by_source:
            continue

        # Use NPPES value as reference; fall back to CMS
        reference_value = (
            values_by_source.get("nppes")
            or values_by_source.get("cms")
            or next(iter(values_by_source.values()))
        )

        if reference_value and reference_value.upper() != old_value.upper():
            diffs.append(FieldDiff(
                field=field,
                old_value=old_value,
                new_value=reference_value,
                confidence_score=0.0,   # filled by ScoringAgent
                supporting_sources=[],  # filled by ScoringAgent
            ))

    return {**state, "diffs": diffs}
