"""
Retrieval-before-generation layer, two phases.

The guide is explicit: "The guidelines require product data to come from
the manufacturer's own site or documentation. Marketplaces and distributor
sites are explicitly excluded." A generic web search violates this the
moment it surfaces an Amazon or Ferguson listing, so retrieval here is
domain-aware in both phases:

  Phase 1 (identity) - brand is often unknown from the raw input alone
  (placeholder brand fields are common). Search the open web to identify
  the manufacturer, but explicitly EXCLUDE known marketplace/distributor
  domains so identity guesses aren't laundered through a reseller listing.

  Phase 2 (spec grounding) - once a manufacturer is identified (via
  normalization.match_manufacturer_brand), restrict the search to that
  manufacturer's own domain only, via Tavily's include_domains. Sources
  from this phase are the only ones allowed to grant HIGH/MEDIUM
  confidence on spec attributes.
"""

import os
from tavily import TavilyClient

_client: TavilyClient | None = None

# Sourcing rule enforcement: never let these count as a grounding source,
# even if they show up in an open search.
EXCLUDED_MARKETPLACE_DISTRIBUTOR_DOMAINS = [
    "amazon.com", "homedepot.com", "lowes.com", "ebay.com", "walmart.com",
    "ferguson.com", "grainger.com", "build.com", "wayfair.com",
    "mcmaster.com", "supplyhouse.com", "faucetdirect.com", "houzz.com",
]


def get_client() -> TavilyClient:
    global _client
    if _client is None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY not set - copy .env.example to .env and fill it in")
        _client = TavilyClient(api_key=api_key)
    return _client


def find_identity_sources(mfg_part_num: str, part_desc: str, max_results: int = 5) -> list[dict]:
    """Phase 1: identify the manufacturer/brand, excluding marketplaces
    and distributors so the identity guess isn't sourced from a reseller."""
    query = f"{mfg_part_num} {part_desc} faucet manufacturer"
    client = get_client()
    try:
        response = client.search(
            query=query, max_results=max_results, search_depth="basic",
            exclude_domains=EXCLUDED_MARKETPLACE_DISTRIBUTOR_DOMAINS,
        )
        return [
            {"url": r["url"], "title": r.get("title", ""), "content": r.get("content", "")}
            for r in response.get("results", [])
        ]
    except Exception as e:
        print(f"[retrieval] identity search failed for {mfg_part_num}: {e}")
        return []


import re

def _mentions_part_number(source: dict, mfg_part_num: str) -> bool:
    """A genuine manufacturer spec page for a specific SKU should mention
    that SKU somewhere (URL, title, or body). This is the check that was
    MISSING before: without it, a domain-restricted search can still
    return a real-but-irrelevant page (e.g. a generic collection page)
    for a part number that doesn't exist, and the LLM would extract
    "verified" specs from it anyway. Normalizes both sides to
    alphanumeric-only before comparing, so formatting differences
    (hyphens, spaces, case) don't cause false negatives."""
    normalized_part = re.sub(r"[^a-z0-9]", "", mfg_part_num.lower())
    if not normalized_part:
        return False
    haystack = re.sub(r"[^a-z0-9]", "",
                       (source.get("url", "") + " " + source.get("title", "") + " " +
                        source.get("content", "")).lower())
    return normalized_part in haystack


def find_manufacturer_sources(mfg_part_num: str, part_desc: str, manufacturer_domain: str,
                               max_results: int = 5) -> list[dict]:
    """Phase 2: pull specs ONLY from the identified manufacturer's own
    domain, AND only pages that actually mention this specific part
    number - a domain match alone isn't enough (see _mentions_part_number
    docstring). Empty result means no manufacturer-verified specs exist
    for THIS part - callers must treat that as low confidence, not fall
    back silently to an unrestricted search or a generic same-domain page."""
    query = f"{mfg_part_num} {part_desc} specifications"
    client = get_client()
    try:
        response = client.search(
            query=query, max_results=max_results, search_depth="advanced",
            include_domains=[manufacturer_domain],
        )
        results = [
            {"url": r["url"], "title": r.get("title", ""), "content": r.get("content", "")}
            for r in response.get("results", [])
        ]
        return [s for s in results if _mentions_part_number(s, mfg_part_num)]
    except Exception as e:
        print(f"[retrieval] manufacturer search failed for {mfg_part_num} on {manufacturer_domain}: {e}")
        return []
