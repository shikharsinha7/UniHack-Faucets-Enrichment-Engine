"""
Unit-of-measure abbreviation standard - a small, faucets-relevant subset
standing in for Unilog's proprietary Unilog_Master_UOM_Standards_
Abbreviations_and_Terms.xlsx (~500 rows across 89 measurement types,
not distributed to participants - see README.md).

Rule from the guide, applied here: always keep a space between the number
and the unit ("24 in", not "24in"), and use exactly one approved
abbreviation per unit type - never "inches", "IN.", or "inch".
"""

# maps any variant spelling -> the single approved abbreviation
UOM_MAP = {
    "inch": "in", "inches": "in", "in.": "in", "in": "in", '"': "in",
    "gallon per minute": "gpm", "gallons per minute": "gpm", "gpm": "gpm",
    "pound": "lb", "pounds": "lb", "lbs": "lb", "lb": "lb",
    "pound per square inch": "psi", "psi": "psi",
    "volt": "V", "volts": "V", "v": "V",
    "amp": "A", "amps": "A", "ampere": "A", "a": "A",
    "decibel": "dBA", "decibels": "dBA", "dba": "dBA",
}


def normalize_uom(raw: str) -> str:
    """Return the single approved abbreviation for a unit, or the raw
    value unchanged if it's not in our (small, curated) map."""
    if not raw:
        return raw
    return UOM_MAP.get(raw.strip().lower(), raw.strip())


def format_value_with_uom(value: str, uom: str | None) -> str:
    """Enforce 'number space unit' spacing per the house-style rule."""
    if not uom:
        return value
    approved = normalize_uom(uom)
    value = value.strip()
    # avoid double-appending if the model already included the unit
    if value.lower().endswith(approved.lower()):
        return value
    return f"{value} {approved}"
