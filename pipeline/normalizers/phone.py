import phonenumbers


def normalize_phone(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""

    try:
        parsed = phonenumbers.parse(raw, "US")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass

    return ""
