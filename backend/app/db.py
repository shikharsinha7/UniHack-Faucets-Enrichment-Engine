"""
Persistence layer. Defaults to SQLite (zero setup, works immediately) so
you're not blocked on a Supabase signup mid-hackathon. To use real
Postgres later: set DATABASE_URL in .env to a postgresql:// connection
string - nothing else in this file or main.py needs to change.

Storage strategy: the full EnrichedProduct is kept as JSON (data_json),
with a few columns pulled out and indexed (mfg_part_num,
needs_human_review, overall_confidence) so the review-queue and listing
endpoints can query without deserializing every row.
"""

import os
import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base

from .models import EnrichedProduct

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BACKEND_DIR / "faucets.db"
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"

raw_db_url = (os.environ.get("DATABASE_URL") or "").strip()
if not raw_db_url or "user:password@host" in raw_db_url:
    DATABASE_URL = DEFAULT_SQLITE_URL
else:
    DATABASE_URL = raw_db_url

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class ProductRecord(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mfg_part_num = Column(String, index=True)
    part_desc = Column(String)
    needs_human_review = Column(Boolean, index=True)
    overall_confidence = Column(String)
    data_json = Column(Text)  # full EnrichedProduct, serialized
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def save_product(product: EnrichedProduct) -> None:
    session = SessionLocal()
    try:
        record = ProductRecord(
            mfg_part_num=product.mfg_part_num,
            part_desc=product.part_desc,
            needs_human_review=product.needs_human_review,
            overall_confidence=product.overall_confidence.value,
            data_json=product.model_dump_json(by_alias=True),
        )
        session.add(record)
        session.commit()
    finally:
        session.close()


def save_products(products: list[EnrichedProduct]) -> None:
    if not products:
        return
    session = SessionLocal()
    try:
        records = [
            ProductRecord(
                mfg_part_num=product.mfg_part_num,
                part_desc=product.part_desc,
                needs_human_review=product.needs_human_review,
                overall_confidence=product.overall_confidence.value,
                data_json=product.model_dump_json(by_alias=True),
            )
            for product in products
        ]
        session.add_all(records)
        session.commit()
    finally:
        session.close()


def _row_to_product(row: ProductRecord) -> dict:
    """Return the stored product plus a couple of DB-level fields (id,
    created_at) merged in - useful for the frontend to show recency /
    have a stable key without parsing timestamps out of the JSON."""
    data = EnrichedProduct.model_validate_json(row.data_json).model_dump(by_alias=True)
    data["_id"] = row.id
    data["_created_at"] = row.created_at.isoformat() if row.created_at else None
    return data


def list_products(limit: int = 100) -> list[dict]:
    session = SessionLocal()
    try:
        rows = (session.query(ProductRecord)
                .order_by(ProductRecord.created_at.desc(), ProductRecord.id.desc())
                .limit(limit)
                .all())
        return [_row_to_product(r) for r in rows]
    finally:
        session.close()


def list_review_queue(limit: int = 100) -> list[dict]:
    session = SessionLocal()
    try:
        rows = (session.query(ProductRecord)
                .filter(ProductRecord.needs_human_review == True)  # noqa: E712
                .order_by(ProductRecord.created_at.desc(), ProductRecord.id.desc())
                .limit(limit)
                .all())
        return [_row_to_product(r) for r in rows]
    finally:
        session.close()
