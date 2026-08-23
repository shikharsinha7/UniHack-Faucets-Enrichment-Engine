"""
Faucets List of Values (LOV) - a hand-curated stand-in for Unilog's
proprietary FAUCETS_LOV.xlsx.

IMPORTANT CONTEXT: the hackathon Solution Guide describes FAUCETS_LOV.xlsx
(permitted attribute values, definitions, title word order) as one of
seven reference files, but this file was never actually distributed to
participants via the dashboard - only the Solution Guide, a 1,000-row
sample input, and a single worked example (a dishwasher, not a faucet)
were provided. See README.md for the full explanation.

This module is our best-effort reconstruction of what that file's shape
would be, built from how real plumbing distributors (Ferguson, Build.com,
Grainger) structure Kitchen & Bath Sink Faucet attributes, plus real
industry certification programs (WaterSense, cUPC, ADA, NSF/ANSI 61).

Architecture note: this is deliberately isolated in one module so a judge
(or a future you) could drop in the real Unilog LOV file by replacing only
this dict - nothing else in the pipeline needs to change. That swappability
is itself worth stating explicitly in the pitch.
"""

CLASSPATH = "Plumbing & HVAC>Kitchen & Bath Fixtures>Faucets"
DEPT = "Plumbing & HVAC"
CLASS_ = "Kitchen & Bath Fixtures"
FINE = "Faucets"

# Order here defines both generation priority and the fixed title/description
# word order the guide's own worked example implies ("Attribute order...
# are fixed... excellent scope for a demo").
FAUCETS_LOV = {
    "Faucet Type": {
        "sequence": 1, "filterable": True, "uom": None,
        "values": ["Kitchen Faucet", "Bathroom Sink Faucet", "Bar/Prep Faucet",
                    "Roman Tub Faucet", "Wall-Mount Faucet", "Utility Faucet"],
    },
    "Mounting Type": {
        "sequence": 2, "filterable": True, "uom": None,
        "values": ["Deck Mount", "Wall Mount", "Widespread", "Centerset", "Single Hole"],
    },
    "Number of Handles": {
        "sequence": 3, "filterable": True, "uom": None,
        "values": ["1", "2", "3"],
    },
    "Handle Type": {
        "sequence": 4, "filterable": False, "uom": None,
        "values": ["Lever", "Cross", "Knob", "Touch/Touchless"],
    },
    "Spout Type": {
        "sequence": 5, "filterable": True, "uom": None,
        "values": ["Pull-Down", "Pull-Out", "Gooseneck", "Standard", "High-Arc"],
    },
    "Spout Height": {
        "sequence": 6, "filterable": False, "uom": "in",
        "values": None, "numeric_range": (4, 20),
    },
    "Spout Reach": {
        "sequence": 7, "filterable": False, "uom": "in",
        "values": None, "numeric_range": (4, 12),
    },
    "Flow Rate": {
        "sequence": 8, "filterable": True, "uom": "gpm",
        "values": None, "numeric_range": (0.5, 2.5),
    },
    "Valve Type": {
        "sequence": 9, "filterable": False, "uom": None,
        "values": ["Ceramic Disc", "Compression", "Ball", "Cartridge"],
    },
    "Number of Faucet Holes": {
        "sequence": 9.5, "filterable": True, "uom": None,
        # a real, distinct spec from Mounting Type - how many deck holes the
        # faucet occupies/accommodates, often expressed as a range like "1 or 3"
        "values": ["1", "2", "3", "1 or 3", "4"],
    },
    "Finish": {
        "sequence": 10, "filterable": True, "uom": None,
        "values": ["Chrome", "Brushed Nickel", "Matte Black", "Oil-Rubbed Bronze",
                    "Stainless Steel", "Polished Brass", "Venetian Bronze"],
    },
    "Material": {
        "sequence": 11, "filterable": True, "uom": None,
        "values": ["Brass", "Zinc Alloy", "Stainless Steel", "Plastic/Polymer"],
    },
    "Certifications": {
        "sequence": 12, "filterable": True, "uom": None,
        # multi-select in practice - validated per-token, not as one string
        "values": ["WaterSense", "cUPC Listed", "ADA Compliant", "ADA", "NSF/ANSI 61",
                    "IAPMO Certified", "CSA B651", "ASME A112.18.1/CSA B125.1",
                    "NSF/ANSI 372", "DOE", "CalGreen"],
        "multi_value": True,
    },
}

# Keyword-based normalization for attributes with heavy manufacturer-specific
# branded naming - mirrors the real LOV file's described "Normalized Label |
# Normalized Values" columns. A raw value is checked against these keyword
# rules BEFORE falling back to exact/fuzzy enum matching, so "Arctic
# Stainless" or "Spot Resist Stainless" (real Moen/Delta finish names) both
# correctly normalize to "Stainless Steel" instead of failing validation.
FINISH_KEYWORD_ALIASES = {
    "stainless": "Stainless Steel",
    "chrome": "Chrome",
    "black": "Matte Black",
    "bronze": "Oil-Rubbed Bronze",
    "brass": "Polished Brass",
    "nickel": "Brushed Nickel",
    "venetian": "Venetian Bronze",
}

VALVE_TYPE_KEYWORD_ALIASES = {
    "diamond seal": "Ceramic Disc",  # Delta's branded name for a ceramic-disc cartridge
    "cartridge": "Cartridge",
    "ceramic": "Ceramic Disc",
    "compression": "Compression",
    "ball": "Ball",
}

ATTRIBUTE_LABELS_IN_ORDER = sorted(FAUCETS_LOV.keys(), key=lambda k: FAUCETS_LOV[k]["sequence"])
