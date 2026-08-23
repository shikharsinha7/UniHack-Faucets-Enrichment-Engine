"""
Schemas modelled on the real Unilog delivery format (252 columns total,
confirmed from the sample Expected_Output CSV) - scoped here to the ~20
columns relevant to a single category (Faucets) plus our confidence/review
layer, per the guide's own advice to go deep on one category rather than
shallow across all 252 columns.

Field names below deliberately echo the real column headers
(MANUFACTURER_NAME, BRAND_NAME, INVOICE_DESC, etc.) so mapping this output
back onto the full 252-column template is a rename, not a redesign.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "high"       # 2+ independent manufacturer-domain sources agree
    MEDIUM = "medium"   # 1 source found, no contradiction
    LOW = "low"         # LLM-inferred with no grounding, or failed LOV validation


class RawProductInput(BaseModel):
    """Mirrors the real 6-column Sample-1000_Items input exactly."""
    mfg_part_num: str = Field(..., examples=["RP19804"])
    part_desc: str = Field(..., examples=["MOEN RP19804 CARTRIDGE KIT CHR"])
    e1_brand: Optional[str] = Field(default=None, examples=["-- Unbranded --"])
    unilog_brand: Optional[str] = Field(default=None, examples=["-- No Unilog Brand --"])
    dib_brand: Optional[str] = Field(default=None, examples=["-- No DIB Brand --"])
    part_manuf: Optional[str] = Field(default=None, examples=["Moen Inc (MOEN01)"])


class EnrichedField(BaseModel):
    value: str
    confidence: ConfidenceLevel
    source: Optional[str] = None
    lov_compliant: Optional[bool] = None  # None = not applicable (e.g. free-text fields)


class EnrichedAttribute(BaseModel):
    label: str
    value: EnrichedField
    uom: Optional[str] = None


class EnrichedProduct(BaseModel):
    # echo of raw input, for traceability
    mfg_part_num: str
    part_desc: str

    # taxonomy - fixed for this single-category build
    dept: str
    class_: str = Field(..., alias="class")
    fine: str
    classpath: str

    # normalized identity
    manufacturer_name: EnrichedField
    brand_name: EnrichedField

    # the four description formats
    invoice_desc: EnrichedField   # <=40 char, CAPS
    mobile_desc: EnrichedField    # 60-80 char
    short_desc: EnrichedField     # product title
    long_desc: EnrichedField      # full description

    attributes: list[EnrichedAttribute]

    needs_human_review: bool
    overall_confidence: ConfidenceLevel

    model_config = {"populate_by_name": True}


class BatchEnrichmentRequest(BaseModel):
    products: list[RawProductInput]


class BatchEnrichmentResponse(BaseModel):
    results: list[EnrichedProduct]
    total: int
    flagged_for_review: int
