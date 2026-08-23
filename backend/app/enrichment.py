"""
Full pipeline for one product, in order:

1. Strip placeholder brand fields ("-- Unbranded --" etc.) from raw input.
2. Try to identify manufacturer/brand directly from the distributor's own
   Part_Manuf field first (cheap, no API call). If that fails, run a
   marketplace-excluded identity search (retrieval.find_identity_sources)
   and try again against the search results.
3. Once a manufacturer is identified, restrict spec retrieval to that
   manufacturer's own domain only (retrieval.find_manufacturer_sources) -
   this is the sourcing-rule enforcement point.
4. Ask Gemini to extract candidate facts (series, feature, attributes)
   from the raw description + manufacturer-only sources, constrained to
   the allowed attribute label list.
5. Validate every attribute value against the Faucets LOV in plain Python
   (normalization.validate_lov_value) - this is the accuracy gate, not
   the LLM's own judgement.
6. Assemble the four description formats deterministically
   (content_rules) with character limits enforced in code.
7. Score confidence per field, roll up to an overall "needs review" flag.
"""

import os
from google import genai
from google.genai import types
from pydantic import BaseModel

from .models import RawProductInput, EnrichedField, EnrichedAttribute, EnrichedProduct, ConfidenceLevel
from .retrieval import find_identity_sources, find_manufacturer_sources
from .confidence import score_field, overall_confidence_from_fields
from .normalization import clean_input_brand_fields, match_manufacturer_brand, validate_lov_value, normalize_attribute_uom
from .content_rules import build_invoice_desc, build_mobile_desc, build_short_desc, build_long_desc
from .data.faucets_lov import ATTRIBUTE_LABELS_IN_ORDER, CLASSPATH, DEPT, CLASS_, FINE

_client: genai.Client | None = None
MODEL_NAME = "gemini-3.5-flash"


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set - copy .env.example to .env and fill it in "
                                "(get a free key at aistudio.google.com/apikey)")
        _client = genai.Client(api_key=api_key)
    return _client


# --- Gemini structured output schema ----------------------------------

class SourcedField(BaseModel):
    value: str
    sources: list[str] = []


class AttributeExtraction(BaseModel):
    label: str
    value: str
    uom: str = ""
    sources: list[str] = []


class GeminiFaucetExtraction(BaseModel):
    series_collection: SourcedField
    feature_highlight: SourcedField
    attributes: list[AttributeExtraction]


def _build_prompt(product: RawProductInput, manufacturer_name: str | None, sources: list[dict]) -> str:
    if sources:
        source_block = "\n\n".join(
            f"SOURCE [{s['url']}]:\n{s['content'][:1500]}" for s in sources
        )
    else:
        source_block = ("(No manufacturer-verified sources were found. Infer cautiously "
                         "from the description alone and leave sources empty for every "
                         "field - do not fabricate a source URL.)")

    return f"""You are extracting structured facts for a Kitchen/Bath Faucet product record.
Your output will be validated against a controlled vocabulary afterward, so
extract your best reading - exact spelling match is not your job.

RAW INPUT:
Manufacturer Part Number: {product.mfg_part_num}
Part Description: {product.part_desc}
Manufacturer: {manufacturer_name or "unknown"}

MANUFACTURER-VERIFIED SOURCES (use ONLY these for factual claims; if empty,
infer cautiously from the description alone):
{source_block}

Allowed attribute labels (use ONLY these, do not invent new ones):
{', '.join(ATTRIBUTE_LABELS_IN_ORDER)}

Extract:
- series_collection: product series/collection name if identifiable, else empty string
- feature_highlight: one standout marketed feature if identifiable (e.g. "Pull-Down Spray"), else empty string
- attributes: as many of the allowed labels as you can determine, each with its value,
  a unit if numeric, and which source URLs actually supported it (empty list if inferred
  without support - never fabricate a source URL that wasn't provided above)."""


def _resolve_manufacturer(product: RawProductInput) -> tuple[dict | None, EnrichedField, EnrichedField, list[dict]]:
    """
    Returns (matched_entry_or_None, manufacturer_field, brand_field, identity_sources_used).
    Tries the distributor's own field first (cheap), falls back to a
    marketplace-excluded web search only if that fails.
    """
    raw_candidates = clean_input_brand_fields(product.part_manuf, product.e1_brand,
                                               product.unilog_brand, product.dib_brand)
    combined_raw = " ".join(raw_candidates)

    entry = match_manufacturer_brand(combined_raw) if combined_raw else None
    if entry:
        manufacturer_field = EnrichedField(
            value=entry["manufacturer_name"], confidence=ConfidenceLevel.MEDIUM,
            source="distributor-supplied Part_Manuf field, matched to master list", lov_compliant=True,
        )
        brand_field = EnrichedField(
            value=entry["brand_name"], confidence=ConfidenceLevel.MEDIUM,
            source="distributor-supplied Part_Manuf field, matched to master list", lov_compliant=True,
        )
        return entry, manufacturer_field, brand_field, []

    # fall back to identity search
    identity_sources = find_identity_sources(product.mfg_part_num, product.part_desc)
    identity_text = " ".join((s["title"] + " " + s["content"]) for s in identity_sources)
    entry = match_manufacturer_brand(identity_text) if identity_text else None
    if entry:
        supporting = [s["url"] for s in identity_sources
                      if any(alias in (s["title"] + s["content"]).lower() for alias in entry["aliases"])]
        conf = score_field(supporting, identity_sources, lov_compliant=True)
        manufacturer_field = EnrichedField(value=entry["manufacturer_name"], confidence=conf,
                                            source=supporting[0] if supporting else None, lov_compliant=True)
        brand_field = EnrichedField(value=entry["brand_name"], confidence=conf,
                                     source=supporting[0] if supporting else None, lov_compliant=True)
        return entry, manufacturer_field, brand_field, identity_sources

    # unresolved - do not fabricate a canonical name
    unresolved = EnrichedField(value="UNVERIFIED", confidence=ConfidenceLevel.LOW,
                                source=None, lov_compliant=False)
    return None, unresolved, unresolved, identity_sources


def enrich_product(product: RawProductInput) -> EnrichedProduct:
    entry, manufacturer_field, brand_field, identity_sources = _resolve_manufacturer(product)

    # Phase 2: manufacturer-restricted spec retrieval - only runs if we
    # actually identified a manufacturer domain to restrict to.
    manufacturer_sources: list[dict] = []
    if entry:
        manufacturer_sources = find_manufacturer_sources(
            product.mfg_part_num, product.part_desc, entry["domain"]
        )

    prompt = _build_prompt(product, manufacturer_field.value if entry else None, manufacturer_sources)

    client = get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeminiFaucetExtraction,
        ),
    )
    data: GeminiFaucetExtraction | None = response.parsed
    if data is None:
        raise RuntimeError(f"Gemini returned unparseable output for {product.mfg_part_num}: {response.text!r}")

    # --- validate + score each attribute against the LOV -----------------
    enriched_attributes: list[EnrichedAttribute] = []
    for raw_attr in data.attributes:
        if raw_attr.label not in ATTRIBUTE_LABELS_IN_ORDER:
            continue  # model invented a label outside our vocabulary - drop it
        normalized_value, lov_ok = validate_lov_value(raw_attr.label, raw_attr.value)
        confidence = score_field(raw_attr.sources, manufacturer_sources, lov_compliant=lov_ok)
        final_value = normalized_value if lov_ok else raw_attr.value  # keep original for review visibility
        uom = normalize_attribute_uom(raw_attr.label, raw_attr.uom) if lov_ok else raw_attr.uom
        enriched_attributes.append(EnrichedAttribute(
            label=raw_attr.label,
            value=EnrichedField(value=final_value, confidence=confidence,
                                 source=raw_attr.sources[0] if raw_attr.sources else None,
                                 lov_compliant=lov_ok),
            uom=uom or None,
        ))

    # item_type comes from the "Faucet Type" attribute if we found one
    faucet_type_attr = next((a for a in enriched_attributes if a.label == "Faucet Type"), None)
    item_type = faucet_type_attr.value.value if faucet_type_attr else "Faucet"
    item_type_conf = faucet_type_attr.value.confidence if faucet_type_attr else ConfidenceLevel.LOW

    series_field = EnrichedField(
        value=data.series_collection.value or "",
        confidence=score_field(data.series_collection.sources, manufacturer_sources),
        source=data.series_collection.sources[0] if data.series_collection.sources else None,
    )
    feature_field = EnrichedField(
        value=data.feature_highlight.value or "",
        confidence=score_field(data.feature_highlight.sources, manufacturer_sources),
        source=data.feature_highlight.sources[0] if data.feature_highlight.sources else None,
    )

    # --- deterministic description assembly -------------------------------
    # exclude "Faucet Type" from the key-attribute list used in descriptions -
    # it's already represented by item_type, including it too produced a
    # visible "KITCHEN FAUCET KITCHEN FAUCET" duplication bug.
    def _display_value(attr: EnrichedAttribute) -> str:
        if attr.label == "Number of Handles":
            return f"{attr.value.value}-Handle"
        if attr.uom:
            return f"{attr.value.value} {attr.uom}"
        return attr.value.value

    non_type_attrs = [a for a in enriched_attributes if a.label != "Faucet Type"]
    key_attr_strings = [_display_value(a) for a in non_type_attrs[:3] if a.value.lov_compliant]
    attribute_strings_full = [
        f"{a.label} = {a.value.value}" + (f" {a.uom}" if a.uom else "")
        for a in enriched_attributes if a.value.lov_compliant
    ]

    invoice_desc = EnrichedField(
        value=build_invoice_desc(item_type, key_attr_strings),
        confidence=item_type_conf, source=None,
    )
    mobile_desc = EnrichedField(
        value=build_mobile_desc(manufacturer_field.value, brand_field.value, item_type,
                                 series_field.value or None, product.mfg_part_num),
        confidence=overall_confidence_from_fields([manufacturer_field, brand_field]),
        source=None,
    )
    short_desc = EnrichedField(
        value=build_short_desc(brand_field.value, series_field.value or None, product.mfg_part_num,
                                item_type, feature_field.value or None, key_attr_strings),
        confidence=overall_confidence_from_fields([brand_field, series_field] + (
            [faucet_type_attr.value] if faucet_type_attr else [])),
        source=None,
    )
    long_desc = EnrichedField(
        value=build_long_desc(brand_field.value, item_type, feature_field.value or None,
                               attribute_strings_full),
        confidence=overall_confidence_from_fields(
            [brand_field] + [a.value for a in enriched_attributes if a.value.lov_compliant]
        ) if enriched_attributes else ConfidenceLevel.LOW,
        source=None,
    )

    all_scored_fields = [manufacturer_field, brand_field, invoice_desc, mobile_desc,
                          short_desc, long_desc] + [a.value for a in enriched_attributes]
    overall = overall_confidence_from_fields(all_scored_fields)

    return EnrichedProduct(
        mfg_part_num=product.mfg_part_num,
        part_desc=product.part_desc,
        dept=DEPT, **{"class": CLASS_}, fine=FINE, classpath=CLASSPATH,
        manufacturer_name=manufacturer_field,
        brand_name=brand_field,
        invoice_desc=invoice_desc,
        mobile_desc=mobile_desc,
        short_desc=short_desc,
        long_desc=long_desc,
        attributes=enriched_attributes,
        needs_human_review=(overall == ConfidenceLevel.LOW),
        overall_confidence=overall,
    )
