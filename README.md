# Faucets Enrichment & Trust Engine

Product-data enrichment for one category, faucets. Given a raw distributor row (part number, description and up to four brand fields), it works out the manufacturer, pulls specifications from the manufacturer's own website, and produces validated attributes plus four listing descriptions. Gemini proposes values; plain Python decides which of them are allowed.

Built in August 2026 for UniHack (Unilog x Hack2Skill). The entry was not submitted.

**Stack:** Python, FastAPI, Pydantic, SQLAlchemy (SQLite by default, Postgres through `DATABASE_URL`), Google Gemini (structured output), Tavily search, React with Vite. Deployed with the frontend on Vercel and the backend on Render's free tier, so the first request after the backend has been idle is slow.

## How it works

Three stages, run per product:

1. **Identify the manufacturer.** Placeholder brand values such as `-- Unbranded --` are stripped. The manufacturer is matched against a curated master list (`app/data/manufacturers.py`), using the distributor's own fields first and a web search as the fallback. The taxonomy is fixed to `Plumbing & HVAC > Kitchen & Bath Fixtures > Faucets`.
2. **Extract attributes against a controlled vocabulary.** Retrieval runs in two phases (`app/retrieval.py`): an identity search that excludes marketplaces and distributors (Amazon, Home Depot, Ferguson and others), then a specification search limited to the manufacturer's own domain through Tavily's `include_domains`. Gemini extracts candidate values from those sources into a fixed schema. Every value is then checked in Python against the faucet vocabulary (`app/data/faucets_lov.py`, `app/normalization.py`), and values outside it are rejected.
3. **Assemble descriptions in code.** The invoice, mobile, short and long descriptions are built from validated facts by `app/content_rules.py`, with the character limits enforced in code: at most 40 characters for the invoice line, 60 to 80 for the mobile line.

**Confidence scoring** (`app/confidence.py`). A field supported by two or more distinct manufacturer sources scores HIGH, one source MEDIUM, none LOW. An attribute that fails the vocabulary check is capped at LOW whatever its sources. A record's overall confidence is its weakest field, and LOW records are flagged for human review.

## About the reference data

The challenge's guide describes seven reference files, including Unilog's content guidelines and the faucet list of values. Only three were distributed to participants: the guide, a 1,000-row sample input and one worked example (a dishwasher). So the vocabulary, the manufacturer list and the description rules here are hand-curated:

- the vocabulary from how plumbing distributors structure faucet attributes and from certification programmes (WaterSense, cUPC, ADA);
- the manufacturer list from the major brands' legal names;
- the description rules from the one worked example.

Each lives in its own module, so real reference files would replace three files and nothing else.

The 1,000-row sample contains no faucets, so testing used real faucet part numbers, for example Moen 7594, Delta 9178-AR-DST and Kohler K-596-VS.

## Run it

Backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # set GEMINI_API_KEY and TAVILY_API_KEY
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## API

| Endpoint | Purpose |
|---|---|
| `POST /enrich` | Enrich one product |
| `POST /enrich/batch` | Enrich a list of products |
| `POST /enrich/upload-csv` | Enrich a CSV in the challenge's six-column format |
| `GET /products` | Saved results, most recent first |
| `GET /products/review-queue` | Saved results flagged for human review |
| `GET /health` | Health check |

## Evaluation

`python -m app.evaluation path/to/batch_response.json` reports character-limit compliance and the share of attribute values found in the vocabulary for any saved batch. Field-level accuracy needs the challenge's 200-row ground-truth file, which was not distributed; `score_against_ground_truth` is ready for it.

## Limitations

- One category only, and the vocabulary is hand-curated rather than Unilog's official list.
- Results depend on two external APIs (Gemini and Tavily); rate limits or outages produce flagged or empty results.
- On Render's free tier the SQLite file lives on an ephemeral disk, so saved results do not survive a redeploy. Set `DATABASE_URL` to a Postgres database to keep them.
- The frontend filters results by flagged and verified; there is no separate review-queue screen.
- No automated tests yet.

Notes from the hackathon itself are in [`docs/hackathon-notes.md`](./docs/hackathon-notes.md).
