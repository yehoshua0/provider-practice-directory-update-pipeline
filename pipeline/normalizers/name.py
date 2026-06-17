import re

_CREDENTIALS = {"MD", "DO", "PhD", "NP", "PA", "DDS", "DPM", "OD", "DC", "RN"}


def normalize_name(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""

    # Check if original has commas (indicates "Last, First" format)
    has_commas = "," in raw

    # Remove commas used as separators (e.g. "Smith, John, MD" → "Smith John MD")
    raw = raw.replace(",", " ")
    tokens = raw.split()

    credentials = []
    name_tokens = []

    for token in tokens:
        upper = token.upper().rstrip(".")
        if upper in {c.upper() for c in _CREDENTIALS}:
            # Preserve canonical casing for the credential
            match = next((c for c in _CREDENTIALS if c.upper() == upper), token)
            credentials.append(match)
        else:
            name_tokens.append(token.capitalize())

    # If format was "Last, First", reorder to "First Last"
    if has_commas and len(name_tokens) >= 2:
        # Reverse the name tokens to put first name first
        name_tokens = name_tokens[::-1]

    parts = name_tokens + credentials
    return " ".join(parts)
