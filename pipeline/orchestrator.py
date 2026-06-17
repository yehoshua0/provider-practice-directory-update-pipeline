import logging
import sqlite3
from datetime import date

from langgraph.graph import StateGraph, END

from pipeline.agents.fetch import fetch_node
from pipeline.agents.normalize import normalize_node
from pipeline.agents.compare import compare_node
from pipeline.agents.score import score_node
from pipeline.agents.router import router_node
from pipeline.agents.staleness import detect_stale
from pipeline.db.audit import log_decision, add_to_review_queue
from pipeline.db.store import upsert_provider
from pipeline.state import PipelineState, ProviderRecord

log = logging.getLogger(__name__)


def _error_handler(state: PipelineState) -> PipelineState:
    log.error("Pipeline error for %s: %s", state["record"]["provider_id"], state.get("error"))
    return {**state, "recommended_action": "no_change",
            "reason": f"Pipeline error: {state.get('error')}"}


def _wrap(node_fn):
    def wrapped(state: PipelineState) -> PipelineState:
        if state.get("error"):
            return state  # already failed; skip this node
        try:
            return node_fn(state)
        except Exception as e:
            return {**state, "error": str(e)}
    return wrapped


def _route_after_fetch(state: PipelineState) -> str:
    if state.get("error"):
        return "error_handler"
    return "normalize"


def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("fetch",         _wrap(fetch_node))
    graph.add_node("normalize",     _wrap(normalize_node))
    graph.add_node("compare",       _wrap(compare_node))
    graph.add_node("score",         _wrap(score_node))
    graph.add_node("route",         _wrap(router_node))
    graph.add_node("error_handler", _error_handler)

    graph.set_entry_point("fetch")
    graph.add_conditional_edges("fetch", _route_after_fetch,
                                 {"normalize": "normalize", "error_handler": "error_handler"})
    graph.add_edge("normalize", "compare")
    graph.add_edge("compare",   "score")
    graph.add_edge("score",     "route")

    def _route_after_route(state: PipelineState) -> str:
        return "error_handler" if state.get("error") else END

    graph.add_conditional_edges("route", _route_after_route,
                                 {"error_handler": "error_handler", END: END})
    graph.add_edge("error_handler", END)

    return graph.compile()


_GRAPH = None


def _get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def run_pipeline(record: ProviderRecord, conn: sqlite3.Connection) -> PipelineState:
    initial: PipelineState = {
        "record": record,
        "raw_sources": {},
        "normalized": {},
        "diffs": [],
        "overall_confidence": 0.0,
        "recommended_action": "no_change",
        "reason": "",
        "error": None,
    }

    result: PipelineState = _get_graph().invoke(initial)

    with conn:
        if result.get("error"):
            # Pipeline failed — record the error but do NOT update last_verified_date
            log_decision(conn, result)
            return result

        if result["recommended_action"] == "auto_update":
            updated = {**record}
            for diff in result["diffs"]:
                updated[diff["field"]] = diff["new_value"]
            updated["last_verified_date"] = date.today().isoformat()
            upsert_provider(conn, updated)

        elif result["recommended_action"] == "human_review":
            add_to_review_queue(conn, result)
            record_copy = {**record, "last_verified_date": date.today().isoformat()}
            upsert_provider(conn, record_copy)

        else:
            record_copy = {**record, "last_verified_date": date.today().isoformat()}
            upsert_provider(conn, record_copy)

        log_decision(conn, result)

    return result


def run_batch(conn: sqlite3.Connection, days: int = 90) -> list[PipelineState]:
    stale = detect_stale(conn, days=days)
    log.info("Processing %d stale records", len(stale))
    results = []
    for record in stale:
        try:
            results.append(run_pipeline(record, conn))
        except Exception as e:
            log.error("run_batch: unhandled error for %s: %s", record["provider_id"], e)
    return results
