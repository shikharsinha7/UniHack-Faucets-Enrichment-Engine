"""
Manufacturer/brand master list - a curated stand-in for Unilog's proprietary
UniCat_Manufacturer_and_Brand_List.xlsx (27,000+ rows, not distributed to
participants - see README.md).

Real faucet manufacturers/brands, with exact legal casing and ® / (R)
symbols as they'd actually appear on a manufacturer's own site - this
mirrors the real file's stated purpose: normalise messy supplier strings
to one canonical (manufacturer, brand) pair.

Each entry also carries the manufacturer's own domain, used to restrict
web retrieval to manufacturer-owned sources per the sourcing rule
("manufacturer's own site or documentation... marketplaces and
distributor sites are explicitly excluded").
"""

MANUFACTURER_BRAND_LIST = [
    {
        "manufacturer_name": "Moen Incorporated",
        "manufacturer_code": "MOEN",
        "brand_name": "Moen\u00ae",
        "brand_code": "MOEN",
        "domain": "moen.com",
        "aliases": ["moen", "moen inc", "moen incorporated"],
    },
    {
        "manufacturer_name": "Delta Faucet Company",
        "manufacturer_code": "DELTA",
        "brand_name": "Delta\u00ae",
        "brand_code": "DELTA",
        "domain": "deltafaucet.com",
        "aliases": ["delta", "delta faucet", "delta faucet co"],
    },
    {
        "manufacturer_name": "Kohler Co.",
        "manufacturer_code": "KOHLER",
        "brand_name": "KOHLER\u00ae",
        "brand_code": "KOHLER",
        "domain": "kohler.com",
        "aliases": ["kohler", "kohler co", "kohler company"],
    },
    {
        "manufacturer_name": "American Standard Brands",
        "manufacturer_code": "AMSTD",
        "brand_name": "American Standard\u00ae",
        "brand_code": "AMSTD",
        "domain": "americanstandard-us.com",
        "aliases": ["american standard", "amstd", "as brands"],
    },
    {
        "manufacturer_name": "LIXIL Water Technology Americas",
        "manufacturer_code": "GROHE",
        "brand_name": "GROHE",
        "brand_code": "GROHE",
        "domain": "grohe.com",
        "aliases": ["grohe", "grohe america"],
    },
    {
        "manufacturer_name": "Spectrum Brands, Inc.",
        "manufacturer_code": "PFISTER",
        "brand_name": "Pfister\u00ae",
        "brand_code": "PFISTER",
        "domain": "pfisterfaucets.com",
        "aliases": ["pfister", "price pfister"],
    },
    {
        "manufacturer_name": "Fortune Brands Water Innovations",
        "manufacturer_code": "PEERLESS",
        "brand_name": "Peerless\u00ae",
        "brand_code": "PEERLESS",
        "domain": "peerlessfaucet.com",
        "aliases": ["peerless", "peerless faucet"],
    },
    {
        "manufacturer_name": "Newport Brass, Inc.",
        "manufacturer_code": "NEWPORT",
        "brand_name": "Newport Brass\u00ae",
        "brand_code": "NEWPORT",
        "domain": "newportbrass.com",
        "aliases": ["newport brass", "newport"],
    },
    {
        "manufacturer_name": "Kraus USA, LLC",
        "manufacturer_code": "KRAUS",
        "brand_name": "KRAUS",
        "brand_code": "KRAUS",
        "domain": "kraususa.com",
        "aliases": ["kraus", "kraus usa"],
    },
]

MANUFACTURER_DOMAINS = [m["domain"] for m in MANUFACTURER_BRAND_LIST]
