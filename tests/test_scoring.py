from pipeline.agents.score import score_field, overall_confidence, SOURCE_WEIGHTS
from pipeline.state import FieldDiff

# --- score_field ---

def test_score_field_nppes_only():
    values = {"nppes": "250 HEALTH PARK DR, FORT MYERS, FL 33908"}
    result = score_field("address", values, "100 MAIN ST, NAPLES, FL 34102")
    assert result["confidence_score"] == 1.0
    assert result["supporting_sources"] == ["nppes"]

def test_score_field_nppes_and_cms_agree():
    values = {"nppes": "250 HEALTH PARK DR", "cms": "250 HEALTH PARK DR"}
    result = score_field("address", values, "100 MAIN ST")
    expected = round((SOURCE_WEIGHTS["nppes"] + SOURCE_WEIGHTS["cms"]) /
                     (SOURCE_WEIGHTS["nppes"] + SOURCE_WEIGHTS["cms"]), 4)
    assert result["confidence_score"] == expected  # 1.0
    assert set(result["supporting_sources"]) == {"nppes", "cms"}

def test_score_field_sources_conflict():
    values = {"nppes": "250 HEALTH PARK DR", "cms": "300 DIFFERENT AVE"}
    result = score_field("address", values, "100 MAIN ST")
    # Only nppes agrees with nppes reference
    expected = round(SOURCE_WEIGHTS["nppes"] / (SOURCE_WEIGHTS["nppes"] + SOURCE_WEIGHTS["cms"]), 4)
    assert result["confidence_score"] == expected
    assert result["supporting_sources"] == ["nppes"]

def test_score_field_no_sources():
    result = score_field("address", {}, "100 MAIN ST")
    assert result["confidence_score"] == 0.0
    assert result["supporting_sources"] == []


# --- overall_confidence ---

def test_overall_confidence_no_diffs():
    assert overall_confidence([]) == 1.0

def test_overall_confidence_averages():
    diffs = [
        FieldDiff(field="address", old_value="", new_value="", confidence_score=0.9, supporting_sources=[]),
        FieldDiff(field="phone", old_value="", new_value="", confidence_score=0.7, supporting_sources=[]),
    ]
    assert overall_confidence(diffs) == round((0.9 + 0.7) / 2, 4)
