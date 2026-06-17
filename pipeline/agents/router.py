from pipeline.state import FieldDiff, PipelineState

_AUTO_UPDATE_THRESHOLD  = 0.85
_HUMAN_REVIEW_THRESHOLD = 0.60


def _safe_to_auto_update(diff: FieldDiff) -> bool:
    if diff["field"] == "address":
        return (
            "nppes" in diff["supporting_sources"]
            and len(diff["supporting_sources"]) >= 2
        )
    return diff["confidence_score"] >= _AUTO_UPDATE_THRESHOLD


def router_node(state: PipelineState) -> PipelineState:
    diffs = state["diffs"]
    confidence = state["overall_confidence"]

    if not diffs:
        return {**state, "recommended_action": "no_change",
                "reason": "No changes detected. Record confirmed accurate."}

    if confidence >= _AUTO_UPDATE_THRESHOLD and all(_safe_to_auto_update(d) for d in diffs):
        return {
            **state,
            "recommended_action": "auto_update",
            "reason": (
                f"Updated fields confirmed by multiple reliable sources "
                f"(overall confidence: {confidence})."
            ),
        }

    if confidence >= _HUMAN_REVIEW_THRESHOLD:
        return {
            **state,
            "recommended_action": "human_review",
            "reason": (
                f"Sources conflict or address change lacks secondary confirmation "
                f"(overall confidence: {confidence}). Manual verification recommended."
            ),
        }

    return {
        **state,
        "recommended_action": "no_change",
        "reason": (
            f"Confidence too low to act ({confidence}). "
            "Insufficient source agreement — no change applied."
        ),
    }
