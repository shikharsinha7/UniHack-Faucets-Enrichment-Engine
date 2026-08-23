"""
Content construction formulas - a reconstruction of what
UNILOG_INTERNAL_CONTENT_GUIDELINES.docx would specify, inferred from the
one worked example the Solution Guide actually shows (the Frigidaire
dishwasher) and generalized to Faucets. The real .docx was never
distributed to participants (see README.md) - this is our best-effort
formula set, built to the same *shape* the guide demonstrates:

    INVOICE_DESC   <=40 char, ALL CAPS, heavily abbreviated
    MOBILE_DESC    60-80 char
    SHORT_DESC     Brand + Series + MPN + Item Type + key attributes
    LONG_DESC1     Brand + Item Type + full attribute list, units included

Character limits are enforced HERE, in code, after the LLM has already
supplied the raw facts - not left to the model's judgement. This is a
deliberate design choice worth stating in the pitch: formatting
compliance shouldn't depend on the LLM "remembering" a character limit.
"""

INVOICE_DESC_MAX = 40
MOBILE_DESC_MIN = 60
MOBILE_DESC_MAX = 80


def build_invoice_desc(item_type: str, key_attrs: list[str]) -> str:
    """<=40 char, ALL CAPS, abbreviated - till-receipt style."""
    parts = [item_type] + key_attrs
    text = " ".join(parts).upper()
    if len(text) <= INVOICE_DESC_MAX:
        return text
    # truncate on a word boundary rather than mid-word
    truncated = text[:INVOICE_DESC_MAX]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated


def build_mobile_desc(manufacturer_name: str, brand_name: str, item_type: str,
                       series: str | None, mpn: str) -> str:
    """60-80 char - mobile app search result style."""
    parts = [manufacturer_name, brand_name, item_type]
    if series:
        parts.append(series)
    parts.append(mpn)
    text = ", ".join(p for p in parts if p)

    if len(text) < MOBILE_DESC_MIN:
        # Pad with a qualifier, but never repeat a word already present
        # (e.g. don't append ", Faucet" to a string that already says
        # "Kitchen Faucet" - reads redundant). Try candidates in order,
        # skip any whose keyword already appears.
        text_lower = text.lower()
        candidates = [
            (", Faucet", "faucet"),
            (", Kitchen & Bath Fixture", "kitchen & bath"),
            (", Plumbing Fixture", "plumbing"),
            (", Genuine OEM Part", "oem"),
        ]
        for suffix, keyword in candidates:
            if keyword not in text_lower:
                text = text + suffix
                break

    if len(text) > MOBILE_DESC_MAX:
        truncated = text[:MOBILE_DESC_MAX]
        if "," in truncated:
            truncated = truncated.rsplit(",", 1)[0]
        text = truncated
    return text


def build_short_desc(brand_name: str, series: str | None, mpn: str, item_type: str,
                      feature_highlight: str | None, key_attrs: list[str]) -> str:
    """Product title - Brand + Series + MPN + Item Type + key attributes,
    'With <feature>' clause mirrors the worked example's CleanBoost pattern."""
    lead = f"{brand_name} {series} {mpn} {item_type}".replace("  ", " ").strip()
    tail_parts = []
    if feature_highlight:
        tail_parts.append(f"With {feature_highlight}")
    tail_parts.extend(key_attrs)
    tail = ", ".join(tail_parts)
    return f"{lead}, {tail}" if tail else lead


def build_long_desc(brand_name: str, item_type: str, feature_highlight: str | None,
                     attribute_strings: list[str]) -> str:
    """Full description - Brand + Item Type + feature + every attribute
    with its unit, comma-joined, matching the worked example's density."""
    lead = f"{brand_name} {item_type}"
    if feature_highlight:
        lead += f" With {feature_highlight}"
    parts = [lead] + attribute_strings
    return ", ".join(parts)
