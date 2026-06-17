import pytest
import httpx
from unittest.mock import patch, MagicMock
from pipeline.sources.nppes import fetch_nppes
from pipeline.sources.cms import fetch_cms
from pipeline.sources.board.florida import fetch_florida_board
from pipeline.sources.website import fetch_website

NPPES_RESPONSE = {
    "result_count": 1,
    "results": [{
        "number": "1234567890",
        "basic": {
            "first_name": "JOHN",
            "last_name": "SMITH",
            "credential": "MD",
            "status": "A",
        },
        "addresses": [{
            "address_purpose": "LOCATION",
            "address_1": "250 HEALTH PARK DR",
            "address_2": "",
            "city": "FORT MYERS",
            "state": "FL",
            "postal_code": "33908",
            "telephone_number": "239-555-9000",
        }],
        "taxonomies": [{
            "code": "207RC0000X",
            "desc": "Cardiovascular Disease",
            "primary": True,
        }],
        "praticeLocations": [],
    }]
}

CMS_RESPONSE = {
    "results": [{
        "npi": "1234567890",
        "lst_nm": "SMITH",
        "frst_nm": "JOHN",
        "pri_spec": "CARDIOVASCULAR DISEASE",
        "org_nm": "FORT MYERS HEART CENTER",
    }]
}


def test_fetch_nppes_returns_fields():
    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = NPPES_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = fetch_nppes("1234567890")

    assert result is not None
    assert result["provider_name"] == "John Smith Md"
    assert "FORT MYERS" in result["address"]
    assert result["phone"] == "239-555-9000"
    assert result["specialty"] == "Cardiovascular Disease"
    assert result["active"] is True


def test_fetch_nppes_not_found():
    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result_count": 0, "results": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = fetch_nppes("0000000000")

    assert result is None


def test_fetch_nppes_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("timeout")
        result = fetch_nppes("1234567890")

    assert result is None


def test_fetch_cms_returns_fields():
    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = CMS_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = fetch_cms("1234567890")

    assert result is not None
    assert result["specialty"] == "CARDIOVASCULAR DISEASE"
    assert result["active"] is True


def test_fetch_cms_not_found():
    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = fetch_cms("0000000000")

    assert result is None


def test_fetch_florida_board_returns_none_on_scrape_error():
    with patch("pipeline.sources.board.florida.PlayWrightFetcher") as mock_cls:
        mock_cls.return_value.fetch.side_effect = Exception("scrape error")
        result = fetch_florida_board("1234567890", "John Smith")

    assert result is None


def test_fetch_website_returns_none_on_empty_url():
    result = fetch_website("")
    assert result is None


def test_fetch_website_returns_none_on_all_failures():
    with patch("pipeline.sources.website._fetch_with_scrapling", side_effect=Exception("fail")), \
         patch("pipeline.sources.website._fetch_with_bs4", side_effect=Exception("fail")), \
         patch("pipeline.sources.website._fetch_with_llm", return_value=None):
        result = fetch_website("https://example.com")

    assert result is None
