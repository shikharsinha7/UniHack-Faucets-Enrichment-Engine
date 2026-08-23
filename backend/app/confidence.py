"""
Confidence scoring rules.

Two independent signals feed into a field's confidence, and either one
can force it down - this is intentional:

1. SOURCE AGREEMENT - how many independent manufacturer-domain sources
   supported the value (unchanged from the original design).
2. LOV COMPLIANCE - for attribute values, whether the value actually
   exists in the controlled vocabulary. A value with 3 supporting sources
   that still isn't a permitted LOV value must NOT score HIGH - per the
   guide, "a fluent description made of invented values scores zero,"
   so an off-vocabulary value is disqualifying regardless of how well
   "sourced" it looks.
"""

from .models import ConfidenceLevel


def score_field(supporting_urls: list[str], all_sources: list[dict],
                 lov_compliant: bool | None = None) -> ConfidenceLevel:
    """
    lov_compliant:
        True  -> value matched the controlled vocabulary, score normally
        False -> value failed LOV validation, HARD CAP at LOW regardless
                 of sourcing - an off-vocabulary value is not usable
                 output no matter how well "sourced" it looks
        None  -> not an LOV-constrained field (e.g. a free-text
                 description), score on sourcing alone
    """
    if lov_compliant is False:
        return ConfidenceLevel.LOW

    distinct = set(supporting_urls)
    if len(distinct) >= 2:
        return ConfidenceLevel.HIGH
    if len(distinct) == 1:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def overall_confidence_from_fields(fields) -> ConfidenceLevel:
    """
    Overall record confidence = weakest link. A catalog record with one
    fabricated or off-vocabulary field is not a trustworthy record, even
    if the other fields are well-sourced.
    """
    levels = [f.confidence for f in fields]
    if ConfidenceLevel.LOW in levels:
        return ConfidenceLevel.LOW
    if ConfidenceLevel.MEDIUM in levels:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.HIGH
