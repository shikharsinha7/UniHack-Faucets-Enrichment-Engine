"""
Evaluation harness - measures the three metrics the Solution Guide
explicitly says judges will look for:

    "Field-level accuracy against the 200 known-good rows, character-limit
    compliance, and percentage of values found in the LOV are all simple,
    credible metrics. Judges will look for them."

Two of the three (character-limit compliance, % LOV-matched) can be
computed on ANY batch of output, with no ground truth needed - run this
against your own test batch and put the numbers on your deck.

The third (field-level accuracy against ground truth) needs the real
200-item Unilog-Sample_200_Items-Input-vs-Output.xlsx, which was never
distributed to participants. If you obtain it, `score_against_ground_truth`
below is ready to use - just map its columns to our field names.

Run standalone: python -m app.evaluation <path-to-a-batch-response.json>
"""

import json
import sys
from .models import EnrichedProduct
from .content_rules import INVOICE_DESC_MAX, MOBILE_DESC_MIN, MOBILE_DESC_MAX


def character_limit_compliance(products: list[EnrichedProduct]) -> dict:
    """% of records whose INVOICE_DESC and MOBILE_DESC actually respect
    the guide's stated character limits."""
    if not products:
        return {"invoice_desc_compliant_pct": 0, "mobile_desc_compliant_pct": 0}

    invoice_ok = sum(1 for p in products if len(p.invoice_desc.value) <= INVOICE_DESC_MAX)
    mobile_ok = sum(1 for p in products
                     if MOBILE_DESC_MIN <= len(p.mobile_desc.value) <= MOBILE_DESC_MAX)

    return {
        "invoice_desc_compliant_pct": round(100 * invoice_ok / len(products), 1),
        "mobile_desc_compliant_pct": round(100 * mobile_ok / len(products), 1),
        "n": len(products),
    }


def lov_match_rate(products: list[EnrichedProduct]) -> dict:
    """% of generated attribute values that actually validated against
    the Faucets LOV (lov_compliant=True), vs. how many were dropped."""
    total_attrs = 0
    compliant_attrs = 0
    for p in products:
        for attr in p.attributes:
            total_attrs += 1
            if attr.value.lov_compliant:
                compliant_attrs += 1

    pct = round(100 * compliant_attrs / total_attrs, 1) if total_attrs else 0
    return {
        "lov_compliant_pct": pct,
        "total_attributes_generated": total_attrs,
        "compliant_attributes": compliant_attrs,
    }


def review_flag_rate(products: list[EnrichedProduct]) -> dict:
    """How often the trust layer actually fires - useful to show judges
    the flag isn't decorative (all-green or all-red would both be
    suspicious)."""
    if not products:
        return {"flagged_pct": 0}
    flagged = sum(1 for p in products if p.needs_human_review)
    return {"flagged_pct": round(100 * flagged / len(products), 1), "flagged": flagged, "n": len(products)}


def score_against_ground_truth(products: list[EnrichedProduct], ground_truth_rows: list[dict]) -> dict:
    """
    Field-level accuracy against the real 200-item ground truth, IF you
    obtain Unilog-Sample_200_Items-Input-vs-Output.xlsx.

    ground_truth_rows: list of dicts keyed by the real Unilog column names
    (MANUFACTURER_NAME, BRAND_NAME, INVOICE_DESC, MOBILE_DESC, SHORT_DESC,
    LONG_DESC1, ...), one per row, aligned by Mfg_Part_Num to `products`.
    """
    gt_by_part = {row["Mfg_Part_Num"]: row for row in ground_truth_rows}
    field_matches = {"manufacturer_name": 0, "brand_name": 0, "invoice_desc": 0,
                      "mobile_desc": 0, "short_desc": 0, "long_desc": 0}
    n = 0
    for p in products:
        gt = gt_by_part.get(p.mfg_part_num)
        if not gt:
            continue
        n += 1
        if p.manufacturer_name.value.strip().lower() == gt.get("MANUFACTURER_NAME", "").strip().lower():
            field_matches["manufacturer_name"] += 1
        if p.brand_name.value.strip().lower() == gt.get("BRAND_NAME", "").strip().lower():
            field_matches["brand_name"] += 1
        if p.invoice_desc.value.strip().lower() == gt.get("INVOICE_DESC", "").strip().lower():
            field_matches["invoice_desc"] += 1
        if p.mobile_desc.value.strip().lower() == gt.get("MOBILE_DESC", "").strip().lower():
            field_matches["mobile_desc"] += 1
        if p.short_desc.value.strip().lower() == gt.get("SHORT_DESC", "").strip().lower():
            field_matches["short_desc"] += 1
        if p.long_desc.value.strip().lower() == gt.get("LONG_DESC1", "").strip().lower():
            field_matches["long_desc"] += 1

    if n == 0:
        return {"error": "no matching Mfg_Part_Num found between output and ground truth"}
    return {"n_matched_rows": n, **{f"{k}_accuracy_pct": round(100 * v / n, 1) for k, v in field_matches.items()}}


def run_full_report(products: list[EnrichedProduct]) -> dict:
    return {
        "character_limit_compliance": character_limit_compliance(products),
        "lov_match_rate": lov_match_rate(products),
        "review_flag_rate": review_flag_rate(products),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.evaluation <path-to-batch-response.json>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        raw = json.load(f)
    products = [EnrichedProduct.model_validate(r) for r in raw.get("results", raw)]
    report = run_full_report(products)
    print(json.dumps(report, indent=2))
