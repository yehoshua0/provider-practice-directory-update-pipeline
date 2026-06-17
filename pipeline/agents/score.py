from pipeline.state import FieldDiff, PipelineState

SOURCE_WEIGHTS: dict[str, float] = {
    "nppes":   1.00,
    "cms":     0.85,
    "board":   0.80,
    "website": 0.65,
}


def score_field(
    field: str,
    values_by_source: dict[str, str],
    old_value: str,
) -> FieldDiff:
    if not values_by_source:
        return FieldDiff(
            field=field, old_value=old_value, new_value="",
            confidence_score=0.0, supporting_sources=[],
        )

    reference = (
        values_by_source.get("nppes")
        or values_by_source.get("cms")
        or next(iter(values_by_source.values()))
    )

    agreeing = [
        s for s, v in values_by_source.items()
        if v.upper() == reference.upper()
    ]
    weighted_agree = sum(SOURCE_WEIGHTS.get(s, 0.5) for s in agreeing)
    max_possible   = sum(SOURCE_WEIGHTS.get(s, 0.5) for s in values_by_source)
    confidence     = round(weighted_agree / max_possible, 4) if max_possible else 0.0

    return FieldDiff(
        field=field,
        old_value=old_value,
        new_value=reference,
        confidence_score=confidence,
        supporting_sources=agreeing,
    )


def overall_confidence(diffs: list[FieldDiff]) -> float:
    if not diffs:
        return 1.0
    return round(sum(d["confidence_score"] for d in diffs) / len(diffs), 4)


def score_node(state: PipelineState) -> PipelineState:
    record = state["record"]
    normalized = state["normalized"]

    scored_diffs: list[FieldDiff] = []
    for diff in state["diffs"]:
        field = diff["field"]
        values_by_source = {
            src: str(norm.get(field, ""))
            for src, norm in normalized.items()
            if norm.get(field, "")
        }
        scored_diffs.append(
            score_field(field, values_by_source, str(record.get(field, "")))
        )

    conf = overall_confidence(scored_diffs)
    return {**state, "diffs": scored_diffs, "overall_confidence": conf}
