import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)

_NPPES_URL = "https://npiregistry.cms.hhs.gov/api/"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _get(npi: str) -> dict:
    resp = httpx.get(_NPPES_URL, params={"number": npi, "version": "2.1"}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_nppes(npi: str) -> dict | None:
    try:
        data = _get(npi)
    except Exception as e:
        log.warning("NPPES fetch failed for %s: %s", npi, e)
        return None

    if not data.get("results"):
        return None

    result = data["results"][0]
    basic = result.get("basic", {})

    location = next(
        (a for a in result.get("addresses", []) if a.get("address_purpose") == "LOCATION"),
        {}
    )
    taxonomy = next(
        (t for t in result.get("taxonomies", []) if t.get("primary")),
        {}
    )

    name_parts = [
        basic.get("first_name", ""),
        basic.get("last_name", ""),
        basic.get("credential", ""),
    ]
    provider_name = " ".join(p for p in name_parts if p)

    addr_parts = [
        location.get("address_1", ""),
        location.get("address_2", ""),
    ]
    street = " ".join(p for p in addr_parts if p)
    city_state_zip = ", ".join(p for p in [
        location.get("city", ""),
        location.get("state", ""),
    ] if p)
    zipcode = location.get("postal_code", "")
    if zipcode:
        city_state_zip = f"{city_state_zip} {zipcode}".strip()
    address = ", ".join(p for p in [street, city_state_zip] if p)

    return {
        "provider_name": provider_name,
        "address": address,
        "phone": location.get("telephone_number", ""),
        "specialty": taxonomy.get("desc", ""),
        "active": basic.get("status") == "A",
        "practice_name": "",  # NPPES does not carry practice name
    }
