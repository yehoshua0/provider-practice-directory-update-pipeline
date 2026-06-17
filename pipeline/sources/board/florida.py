import logging
import re
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

_SEARCH_URL = "https://mqa-internet.doh.state.fl.us/MQASearchServices/HealthCareProviders"

# Import PlayWrightFetcher at module level for mockability
try:
    from scrapling.fetchers import PlayWrightFetcher
except ImportError:
    PlayWrightFetcher = None  # type: ignore


def fetch_florida_board(npi: str, name: str) -> dict | None:
    """
    Scrapes the FL DOH provider lookup. Tries Scrapling PlayWrightFetcher first;
    falls back to httpx + BS4 on failure.
    """
    try:
        return _fetch_with_scrapling(npi, name)
    except Exception as e:
        log.warning("FL board Scrapling fetch failed for %s: %s — trying httpx", npi, e)

    try:
        return _fetch_with_httpx(npi, name)
    except Exception as e:
        log.warning("FL board httpx fetch failed for %s: %s", npi, e)
        return None


def _fetch_with_scrapling(npi: str, name: str) -> dict | None:
    if PlayWrightFetcher is None:
        raise ImportError("PlayWrightFetcher not available")

    fetcher = PlayWrightFetcher(auto_match=True)
    last_name = name.split()[-1] if name else ""
    page = fetcher.fetch(
        f"{_SEARCH_URL}?LicenseeLastName={last_name}&LicenseType=ME",
        headless=True,
        timeout=20000,
    )
    return _parse_board_html(page.html_content, npi)


def _fetch_with_httpx(npi: str, name: str) -> dict | None:
    import httpx

    last_name = name.split()[-1] if name else ""
    resp = httpx.get(
        _SEARCH_URL,
        params={"LicenseeLastName": last_name, "LicenseType": "ME"},
        timeout=15,
        follow_redirects=True,
    )
    resp.raise_for_status()
    return _parse_board_html(resp.text, npi)


def _parse_board_html(html: str, npi: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table tr")

    for row in rows:
        cells = [td.get_text(strip=True) for td in row.select("td")]
        if not cells:
            continue

        row_text = " ".join(cells)
        if npi not in row_text:
            continue

        status_text = " ".join(cells).upper()
        active = "ACTIVE" in status_text and "EXPIRED" not in status_text

        phone_match = re.search(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}", row_text)
        phone = phone_match.group(0) if phone_match else ""

        return {
            "active": active,
            "specialty": "",  # FL board HTML does not reliably expose specialty
            "address": "",    # address not consistently available in search results
            "phone": phone,
        }

    return None
