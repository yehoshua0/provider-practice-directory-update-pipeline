import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)

_CMS_URL = "https://data.cms.gov/provider-data/api/1/datastore/query/mj5m-pzi6/0"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _get(npi: str) -> dict:
    params = {
        "conditions[0][property]": "npi",
        "conditions[0][value]": npi,
        "limit": 1,
    }
    resp = httpx.get(_CMS_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_cms(npi: str) -> dict | None:
    try:
        data = _get(npi)
    except Exception as e:
        log.warning("CMS fetch failed for %s: %s", npi, e)
        return None

    results = data.get("results", [])
    if not results:
        return None

    row = results[0]
    name_parts = [row.get("frst_nm", ""), row.get("lst_nm", "")]
    provider_name = " ".join(p for p in name_parts if p)

    return {
        "provider_name": provider_name,
        "specialty": row.get("pri_spec", ""),
        "practice_name": row.get("org_nm", ""),
        "active": True,  # presence in CMS dataset implies active Medicare enrollment
        "address": "",
        "phone": "",
    }
