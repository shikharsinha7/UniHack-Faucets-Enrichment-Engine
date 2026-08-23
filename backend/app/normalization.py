"""
Deterministic normalization layer - runs AFTER the LLM extracts raw values,
BEFORE anything is assembled into final output.

This split matters for the pitch: the LLM's job is narrow (read text,
extract candidate facts). Whether a value is "correct" is decided here,
in plain Python, against the controlled vocabulary - not by asking the
LLM to police itself. That's a direct answer to "how do you ensure
accuracy" that doesn't rely on trusting the model's own confidence claims.

Placeholder handling: per the guide, "-- Unbranded --", "-- No Unilog
Brand --", "-- No DIB Brand --" mean the field is empty, not a real value -
filtered out before they ever reach the LLM prompt.
"""

import difflib
import re
from .data.manufacturers import MANUFACTURER_BRAND_LIST
from .data.faucets_lov import FAUCETS_LOV, FINISH_KEYWORD_ALIASES, VALVE_TYPE_KEYWORD_ALIASES
from .data.uom import normalize_uom

KEYWORD_ALIASES_BY_ATTRIBUTE = {
    "Finish": FINISH_KEYWORD_ALIASES,
    "Valve Type": VALVE_TYPE_KEYWORD_ALIASES,
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _word_subset_match(value: str, permitted_values: list[str]) -> str | None:
    """Match if every significant word of a permitted LOV value appears
    among the candidate value's words - catches cases like 'Kitchen Faucet'
    matching within 'Pull-down kitchen sink faucet', which whole-string
    similarity (difflib) misses due to the length difference.

    If MORE THAN ONE permitted value matches this way, treat it as the
    same "ambiguous multi-value garbage" signal as the keyword-alias step
    and refuse to guess - this is what catches a garbled string that
    happens to literally contain several valid finish names concatenated
    together (a real extraction bug, not a normalization gap).
    """
    value_tokens = _tokenize(value)
    matches = []
    for permitted in permitted_values:
        permitted_tokens = _tokenize(permitted)
        if permitted_tokens and permitted_tokens.issubset(value_tokens):
            matches.append(permitted)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # prefer the longest (most specific) match ONLY if all matches are
        # substrings of each other (e.g. "Bronze" vs "Oil-Rubbed Bronze") -
        # otherwise it's genuinely ambiguous, refuse.
        matches.sort(key=len, reverse=True)
        longest_tokens = _tokenize(matches[0])
        if all(_tokenize(m).issubset(longest_tokens) for m in matches):
            return matches[0]
        return None
    return None

PLACEHOLDER_VALUES = {
    "-- unbranded --", "-- no unilog brand --", "-- no dib brand --",
    "unbranded", "n/a", "none", "",
}


def is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in PLACEHOLDER_VALUES


def clean_input_brand_fields(*brand_candidates: str | None) -> list[str]:
    """Filter placeholder junk out of the raw brand columns, preserving
    order, before they're used for anything (matching or prompting)."""
    return [b.strip() for b in brand_candidates if b and not is_placeholder(b)]


def match_manufacturer_brand(raw_text: str) -> dict | None:
    """
    Fuzzy-match a raw manufacturer/brand string (or free text containing
    one) against the curated master list. Returns the matched entry dict
    or None if nothing crosses the similarity threshold - callers must
    treat None as "manufacturer unverified, do not fabricate a canonical
    name."
    """
    if not raw_text:
        return None
    raw_lower = raw_text.lower()

    # exact/substring alias match first - cheap and precise
    for entry in MANUFACTURER_BRAND_LIST:
        for alias in entry["aliases"]:
            if alias in raw_lower:
                return entry

    # fall back to fuzzy match against manufacturer names for typos/variants
    names = [e["manufacturer_name"].lower() for e in MANUFACTURER_BRAND_LIST]
    close = difflib.get_close_matches(raw_lower, names, n=1, cutoff=0.6)
    if close:
        for entry in MANUFACTURER_BRAND_LIST:
            if entry["manufacturer_name"].lower() == close[0]:
                return entry
    return None


NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5"}


def _normalize_number_words(text: str) -> str:
    return re.sub(r"\b(one|two|three|four|five)\b",
                  lambda m: NUMBER_WORDS[m.group(1).lower()], text, flags=re.IGNORECASE)


def _validate_single_enum_value(attribute_label: str, value: str, permitted_values: list[str]) -> str | None:
    """Try, in order: exact match, keyword alias, word-subset match, fuzzy
    match. Returns the normalized permitted value, or None if nothing
    clears the bar - callers must not keep an unmatched value.

    Guard against ambiguous multi-value garbage (e.g. a list of every
    finish a product LINE offers, rather than the one finish THIS part
    has): if the keyword-alias step matches more than one distinct target,
    that's a signal the source value bundles multiple options together -
    refuse to alias it rather than silently picking one and hiding a real
    extraction error.
    """
    value_norm = _normalize_number_words(value)
    exact = [v for v in permitted_values if v.lower() == value_norm.strip().lower()]
    if exact:
        return exact[0]

    aliases = KEYWORD_ALIASES_BY_ATTRIBUTE.get(attribute_label, {})
    value_lower = value_norm.lower()
    keyword_hits = {normalized for keyword, normalized in aliases.items() if keyword in value_lower}
    if len(keyword_hits) == 1:
        candidate = next(iter(keyword_hits))
        if candidate in permitted_values:
            return candidate
    # len(keyword_hits) > 1 -> ambiguous multi-value string, deliberately
    # fall through without aliasing rather than guessing which one is right

    subset_match = _word_subset_match(value_norm, permitted_values)
    if subset_match:
        return subset_match

    close = difflib.get_close_matches(value_norm, permitted_values, n=1, cutoff=0.7)
    if close:
        return close[0]
    return None


def validate_lov_value(attribute_label: str, value: str) -> tuple[str | None, bool]:
    """
    Check a generated attribute value against the Faucets LOV.

    Returns (normalized_value, is_lov_compliant).
    - Multi-value attributes (e.g. Certifications): split on comma/slash,
      validate each token independently, keep only the compliant ones.
      Compliant if at least one token matched - callers can still see
      which specific tokens survived in the returned value.
    - Enum attributes: matched via _validate_single_enum_value (exact ->
      keyword alias -> word-subset -> fuzzy). Unmatched = (None, False),
      never keep an out-of-vocabulary value, per "attribute values must
      come from the LOV files... a fluent description made of invented
      values scores zero."
    - Numeric attributes: checked against the allowed range instead of an
      enum list.
    """
    spec = FAUCETS_LOV.get(attribute_label)
    if spec is None:
        return None, False

    if spec.get("multi_value") and spec["values"] is not None:
        tokens = [t.strip() for t in re.split(r"[,/]", value) if t.strip()]
        matched = []
        for token in tokens:
            m = _validate_single_enum_value(attribute_label, token, spec["values"])
            if m and m not in matched:
                matched.append(m)
        if matched:
            return ", ".join(matched), True
        return None, False

    if spec["values"] is not None:
        match = _validate_single_enum_value(attribute_label, value, spec["values"])
        return (match, True) if match else (None, False)

    # numeric attribute - pull the leading number out and range-check it
    m = re.search(r"[\d.]+", value)
    if not m:
        return None, False
    num = float(m.group())
    lo, hi = spec.get("numeric_range", (0, float("inf")))
    if lo <= num <= hi:
        formatted = str(int(num)) if num == int(num) else str(num)
        return formatted, True
    return None, False


def normalize_attribute_uom(attribute_label: str, raw_uom: str | None) -> str | None:
    spec = FAUCETS_LOV.get(attribute_label)
    expected = spec["uom"] if spec else None
    if expected is None:
        return None
    return normalize_uom(raw_uom) if raw_uom else expected
