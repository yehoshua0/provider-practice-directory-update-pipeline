import logging
import os
import re
import json
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

_ADDRESS_RE = re.compile(
    r"\d+\s+[\w\s]+(?:St|Ave|Rd|Dr|Blvd|Way|Ln|Ct|Pl|Pkwy)[\w\s,]*\b[A-Z]{2}\s+\d{5}",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}")


def fetch_website(url: str) -> dict | None:
    if not url:
        return None

    try:
        result = _fetch_with_scrapling(url)
        if result is not None:
            return result
    except Exception as e:
        log.debug("Website Scrapling failed for %s: %s", url, e)

    try:
        result = _fetch_with_bs4(url)
        if result is not None:
            return result
    except Exception as e:
        log.debug("Website BS4 failed for %s: %s", url, e)

    try:
        result = _fetch_with_llm(url)
        if result is not None:
            return result
    except Exception as e:
        log.warning("Website LLM fallback failed for %s: %s", url, e)

    return None


def _fetch_with_scrapling(url: str) -> dict | None:
    from scrapling.fetchers import PlayWrightFetcher

    fetcher = PlayWrightFetcher(auto_match=True)
    page = fetcher.fetch(url, headless=True, timeout=20000)
    return _extract_contact(page.html_content)


def _fetch_with_bs4(url: str) -> dict | None:
    resp = httpx.get(url, timeout=10, follow_redirects=True,
                     headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return _extract_contact(resp.text)


def _fetch_with_llm(url: str) -> dict | None:
    import anthropic

    resp = httpx.get(url, timeout=10, follow_redirects=True,
                     headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(separator=" ", strip=True)[:3000]

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                "Extract the primary office address and phone number from this text. "
                "Reply with JSON only: {\"address\": \"...\", \"phone\": \"...\"}. "
                "Use empty string if not found.\n\n" + page_text
            ),
        }],
    )
    text = message.content[0].text.strip()
    try:
        data = json.loads(text)
        if data.get("address") or data.get("phone"):
            return {"address": data.get("address", ""), "phone": data.get("phone", "")}
    except json.JSONDecodeError:
        pass
    return None


def _extract_contact(html: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")

    # Look for contact-specific sections first
    for selector in ["#contact", ".contact", "[class*='contact']", "[id*='contact']",
                     "[class*='location']", "footer", "address"]:
        section = soup.select_one(selector)
        if section:
            text = section.get_text(separator=" ", strip=True)
            address_match = _ADDRESS_RE.search(text)
            phone_match = _PHONE_RE.search(text)
            if address_match or phone_match:
                return {
                    "address": address_match.group(0) if address_match else "",
                    "phone": phone_match.group(0) if phone_match else "",
                }

    # Full page fallback
    text = soup.get_text(separator=" ", strip=True)
    address_match = _ADDRESS_RE.search(text)
    phone_match = _PHONE_RE.search(text)
    if address_match or phone_match:
        return {
            "address": address_match.group(0) if address_match else "",
            "phone": phone_match.group(0) if phone_match else "",
        }

    return None
