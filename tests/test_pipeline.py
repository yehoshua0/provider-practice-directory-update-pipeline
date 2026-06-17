import sqlite3
from unittest.mock import patch

from pipeline.db.store import init_db, upsert_provider
from pipeline.agents.staleness import detect_stale
from pipeline.agents.fetch import fetch_node
from pipeline.agents.normalize import normalize_node
from pipeline.agents.compare import compare_node
from pipeline.agents.router import router_node
from pipeline.state import FieldDiff, PipelineState, ProviderRecord
from pipeline.orchestrator import run_pipeline


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def _base_state(record: ProviderRecord) -> PipelineState:
    return PipelineState(
        record=record,
        raw_sources={},
        normalized={},
        diffs=[],
        overall_confidence=0.0,
        recommended_action="no_change",
        reason="",
        error=None,
    )


# ---------------------------------------------------------------------------
# Task 8: Staleness Detector
# ---------------------------------------------------------------------------

def test_detect_stale_returns_old_records():
    conn = _make_conn()
    upsert_provider(conn, {
        "provider_id": "OLD_001", "npi": "1111111111",
        "provider_name": "Old Doc MD", "specialty": "FM",
        "practice_name": "Old Practice", "address": "1 Main St",
        "phone": "", "website": "", "active": True,
        "last_verified_date": "2020-01-01",
    })
    upsert_provider(conn, {
        "provider_id": "NEW_001", "npi": "2222222222",
        "provider_name": "New Doc MD", "specialty": "FM",
        "practice_name": "New Practice", "address": "2 Main St",
        "phone": "", "website": "", "active": True,
        "last_verified_date": "2026-06-01",
    })
    conn.commit()

    stale = detect_stale(conn, days=90)
    ids = [r["provider_id"] for r in stale]
    assert "OLD_001" in ids
    assert "NEW_001" not in ids
    conn.close()


# ---------------------------------------------------------------------------
# Task 9: Fetch Agent
# ---------------------------------------------------------------------------

def test_fetch_node_populates_raw_sources():
    record = ProviderRecord(
        provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
        specialty="Cardiology", practice_name="ABC Heart Group",
        address="100 Main St, Naples, FL 34102", phone="239-555-1234",
        website="", active=True, last_verified_date="2023-09-01",
    )
    state = _base_state(record)

    with patch("pipeline.agents.fetch.fetch_nppes", return_value={"provider_name": "John Smith MD", "address": "250 Health Park Dr, Fort Myers, FL 33908", "phone": "239-555-9000", "specialty": "Cardiovascular Disease", "active": True, "practice_name": ""}), \
         patch("pipeline.agents.fetch.fetch_cms", return_value={"provider_name": "John Smith", "specialty": "CARDIOVASCULAR DISEASE", "practice_name": "Fort Myers Heart Center", "active": True, "address": "", "phone": ""}), \
         patch("pipeline.agents.fetch.fetch_florida_board", return_value=None), \
         patch("pipeline.agents.fetch.fetch_website", return_value=None):
        result = fetch_node(state)

    assert "nppes" in result["raw_sources"]
    assert result["raw_sources"]["nppes"] is not None
    assert result["raw_sources"]["cms"] is not None
    assert result["error"] is None


def test_fetch_node_continues_on_source_failure():
    record = ProviderRecord(
        provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
        specialty="Cardiology", practice_name="ABC Heart Group",
        address="100 Main St, Naples, FL 34102", phone="239-555-1234",
        website="", active=True, last_verified_date="2023-09-01",
    )
    state = _base_state(record)

    with patch("pipeline.agents.fetch.fetch_nppes", return_value={"address": "250 Health Park Dr", "phone": "239-555-9000", "provider_name": "John Smith MD", "specialty": "Cardiology", "active": True, "practice_name": ""}), \
         patch("pipeline.agents.fetch.fetch_cms", side_effect=Exception("CMS down")), \
         patch("pipeline.agents.fetch.fetch_florida_board", return_value=None), \
         patch("pipeline.agents.fetch.fetch_website", return_value=None):
        result = fetch_node(state)

    assert result["raw_sources"]["nppes"] is not None
    assert result["raw_sources"]["cms"] is None
    assert result["error"] is None


# ---------------------------------------------------------------------------
# Task 10: Normalize Agent
# ---------------------------------------------------------------------------

def test_normalize_node_normalizes_phone_and_address():
    record = ProviderRecord(
        provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
        specialty="Cardiology", practice_name="ABC Heart Group",
        address="100 Main St, Naples, FL 34102", phone="239-555-1234",
        website="", active=True, last_verified_date="2023-09-01",
    )
    state = _base_state(record)
    state["raw_sources"] = {
        "nppes": {
            "provider_name": "JOHN SMITH MD",
            "address": "250 health park dr, fort myers, fl 33908",
            "phone": "239-555-9000",
            "specialty": "Cardiovascular Disease",
            "active": True,
            "practice_name": "",
        },
        "cms": None,
        "board": None,
        "website": None,
    }

    result = normalize_node(state)

    assert "nppes" in result["normalized"]
    norm = result["normalized"]["nppes"]
    assert norm["phone"] == "+12395559000"
    assert "FORT MYERS" in norm["address"]
    assert "cms" not in result["normalized"]


# ---------------------------------------------------------------------------
# Task 11: Compare Agent
# ---------------------------------------------------------------------------

def test_compare_node_detects_address_change():
    record = ProviderRecord(
        provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
        specialty="Cardiology", practice_name="ABC Heart Group",
        address="100 MAIN ST, NAPLES, FL 34102", phone="+12395551234",
        website="", active=True, last_verified_date="2023-09-01",
    )
    state = _base_state(record)
    state["normalized"] = {
        "nppes": ProviderRecord(
            provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
            specialty="Cardiovascular Disease", practice_name="",
            address="250 HEALTH PARK DR, FORT MYERS, FL 33908",
            phone="+12395559000", website="", active=True,
            last_verified_date="2023-09-01",
        )
    }

    result = compare_node(state)

    fields_changed = [d["field"] for d in result["diffs"]]
    assert "address" in fields_changed
    assert "phone" in fields_changed


def test_compare_node_no_diffs_when_unchanged():
    record = ProviderRecord(
        provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
        specialty="Cardiology", practice_name="ABC Heart Group",
        address="100 MAIN ST, NAPLES, FL 34102", phone="+12395551234",
        website="", active=True, last_verified_date="2023-09-01",
    )
    state = _base_state(record)
    state["normalized"] = {
        "nppes": ProviderRecord(
            provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
            specialty="Cardiology", practice_name="",
            address="100 MAIN ST, NAPLES, FL 34102", phone="+12395551234",
            website="", active=True, last_verified_date="2023-09-01",
        )
    }

    result = compare_node(state)

    assert result["diffs"] == []


# ---------------------------------------------------------------------------
# Task 13: Router Agent
# ---------------------------------------------------------------------------

def test_router_auto_update_high_confidence():
    record = ProviderRecord(
        provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
        specialty="Cardiology", practice_name="ABC Heart Group",
        address="100 MAIN ST, NAPLES, FL 34102", phone="+12395551234",
        website="", active=True, last_verified_date="2023-09-01",
    )
    state = _base_state(record)
    state["overall_confidence"] = 0.92
    state["diffs"] = [FieldDiff(
        field="address",
        old_value="100 MAIN ST, NAPLES, FL 34102",
        new_value="250 HEALTH PARK DR, FORT MYERS, FL 33908",
        confidence_score=0.92,
        supporting_sources=["nppes", "cms"],
    )]

    result = router_node(state)
    assert result["recommended_action"] == "auto_update"


def test_router_human_review_conflicting_sources():
    record = ProviderRecord(
        provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
        specialty="Cardiology", practice_name="ABC Heart Group",
        address="100 MAIN ST, NAPLES, FL 34102", phone="+12395551234",
        website="", active=True, last_verified_date="2023-09-01",
    )
    state = _base_state(record)
    state["overall_confidence"] = 0.61
    state["diffs"] = [FieldDiff(
        field="address",
        old_value="100 MAIN ST",
        new_value="250 HEALTH PARK DR",
        confidence_score=0.61,
        supporting_sources=["nppes"],
    )]

    result = router_node(state)
    assert result["recommended_action"] == "human_review"


def test_router_no_change_when_no_diffs():
    record = ProviderRecord(
        provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
        specialty="Cardiology", practice_name="ABC Heart Group",
        address="100 MAIN ST, NAPLES, FL 34102", phone="+12395551234",
        website="", active=True, last_verified_date="2023-09-01",
    )
    state = _base_state(record)
    state["overall_confidence"] = 1.0
    state["diffs"] = []

    result = router_node(state)
    assert result["recommended_action"] == "no_change"


def test_router_address_requires_two_sources_for_auto_update():
    record = ProviderRecord(
        provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
        specialty="Cardiology", practice_name="ABC Heart Group",
        address="100 MAIN ST, NAPLES, FL 34102", phone="+12395551234",
        website="", active=True, last_verified_date="2023-09-01",
    )
    state = _base_state(record)
    state["overall_confidence"] = 0.90
    state["diffs"] = [FieldDiff(
        field="address",
        old_value="100 MAIN ST",
        new_value="250 HEALTH PARK DR",
        confidence_score=0.90,
        supporting_sources=["nppes"],  # only one source — must require 2
    )]

    result = router_node(state)
    assert result["recommended_action"] == "human_review"


# ---------------------------------------------------------------------------
# Task 14: Orchestrator
# ---------------------------------------------------------------------------

def test_run_pipeline_auto_update_end_to_end():
    conn = _make_conn()
    record = ProviderRecord(
        provider_id="HL_001", npi="1234567890", provider_name="John Smith MD",
        specialty="Cardiology", practice_name="ABC Heart Group",
        address="100 Main St, Naples, FL 34102", phone="239-555-1234",
        website="", active=True, last_verified_date="2023-09-01",
    )
    upsert_provider(conn, record)
    conn.commit()

    nppes_data = {
        "provider_name": "John Smith MD", "specialty": "Cardiovascular Disease",
        "practice_name": "", "active": True,
        "address": "250 Health Park Dr, Fort Myers, FL 33908",
        "phone": "239-555-9000",
    }

    with patch("pipeline.agents.fetch.fetch_nppes", return_value=nppes_data), \
         patch("pipeline.agents.fetch.fetch_cms", return_value={"provider_name": "John Smith", "specialty": "CARDIOVASCULAR DISEASE", "practice_name": "Fort Myers Heart Center", "active": True, "address": "250 Health Park Dr, Fort Myers, FL 33908", "phone": "239-555-9000"}), \
         patch("pipeline.agents.fetch.fetch_florida_board", return_value=None), \
         patch("pipeline.agents.fetch.fetch_website", return_value=None):
        result = run_pipeline(record, conn)

    assert result["recommended_action"] in ("auto_update", "human_review")
    assert result["error"] is None
    assert len(result["diffs"]) > 0
    conn.close()
