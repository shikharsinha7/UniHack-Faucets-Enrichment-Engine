from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import csv
import io

load_dotenv()

from .models import RawProductInput, EnrichedProduct, BatchEnrichmentRequest, BatchEnrichmentResponse
from .enrichment import enrich_product
from .db import init_db, save_product, save_products, list_products, list_review_queue

app = FastAPI(title="Faucets Enrichment & Trust Engine (UniHack)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/enrich", response_model=EnrichedProduct)
def enrich_single(product: RawProductInput):
    try:
        result = enrich_product(product)
        save_product(result)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/enrich/batch", response_model=BatchEnrichmentResponse)
def enrich_batch(request: BatchEnrichmentRequest):
    results = [enrich_product(p) for p in request.products]
    save_products(results)
    flagged = sum(1 for r in results if r.needs_human_review)
    return BatchEnrichmentResponse(results=results, total=len(results), flagged_for_review=flagged)


@app.post("/enrich/upload-csv", response_model=BatchEnrichmentResponse)
async def enrich_csv(file: UploadFile = File(...)):
    """
    Accepts a CSV with the REAL Unilog input columns:
    Mfg_Part_Num, Part_Desc, E1_Brand, Unilog_Brand, DIB_Brand, Part_Manuf
    (exactly matching Sample-1000_Items.xlsx / the provided sample dataset).
    """
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    products = [
        RawProductInput(
            mfg_part_num=row["Mfg_Part_Num"],
            part_desc=row["Part_Desc"],
            e1_brand=row.get("E1_Brand"),
            unilog_brand=row.get("Unilog_Brand"),
            dib_brand=row.get("DIB_Brand"),
            part_manuf=row.get("Part_Manuf"),
        )
        for row in reader
    ]
    if not products:
        raise HTTPException(status_code=400, detail="CSV had no valid rows")

    results = [enrich_product(p) for p in products]
    save_products(results)
    flagged = sum(1 for r in results if r.needs_human_review)
    return BatchEnrichmentResponse(results=results, total=len(results), flagged_for_review=flagged)


@app.get("/products", response_model=list[dict])
def get_products(limit: int = Query(default=100, ge=1, le=1000)):
    """
    Returns all enriched products saved in SQLite/Postgres, most recent first.
    """
    return list_products(limit=limit)


@app.get("/products/review-queue", response_model=list[dict])
def get_review_queue(limit: int = Query(default=100, ge=1, le=1000)):
    """
    Returns only flagged/review-required products (needs_human_review=True), most recent first.
    """
    return list_review_queue(limit=limit)
