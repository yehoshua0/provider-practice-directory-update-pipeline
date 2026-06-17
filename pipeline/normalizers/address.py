import usaddress


def normalize_address(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""

    try:
        tagged, _ = usaddress.tag(raw)
    except usaddress.RepeatedLabelError:
        return raw.upper().strip()

    parts = []
    number = tagged.get("AddressNumber", "")
    street_pre = tagged.get("StreetNamePreDirectional", "")
    street = tagged.get("StreetName", "")
    street_type = tagged.get("StreetNamePostType", "")
    street_post = tagged.get("StreetNamePostDirectional", "")
    unit_type = tagged.get("OccupancyType", "")
    unit_id = tagged.get("OccupancyIdentifier", "")
    city = tagged.get("PlaceName", "")
    state = tagged.get("StateName", "")
    zipcode = tagged.get("ZipCode", "")

    street_line = " ".join(p for p in [number, street_pre, street, street_type, street_post] if p)
    unit_part = " ".join(p for p in [unit_type, unit_id] if p)
    if unit_part:
        street_line = f"{street_line} {unit_part}"

    city_state_zip = ", ".join(p for p in [city, state] if p)
    if zipcode:
        city_state_zip = f"{city_state_zip} {zipcode}" if city_state_zip else zipcode

    parts = [p for p in [street_line, city_state_zip] if p]
    return ", ".join(parts).upper().strip(", ")
