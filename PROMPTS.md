# Prompts for Cursor / Claude Code

Feed one at a time. Test each before moving on.

---

## 0. First run (do this yourself)
Get GEMINI_API_KEY and TAVILY_API_KEY into `backend/.env`, run backend +
frontend, test the 3 real faucet part numbers from README.md. Confirm you
see a mix of HIGH/MEDIUM/LOW confidence and at least one attribute that
gets dropped or flagged (⚠) for failing LOV validation — if everything is
clean, the LOV gate probably isn't actually firing, check that first.

Then run `python -m app.evaluation` (after saving a batch response) and
sanity-check the character-limit-compliance and LOV-match numbers before
building anything else on top.

---

## 1. Wire up CSV batch upload in the frontend
```
The backend already has a working POST /enrich/upload-csv endpoint
accepting the real 6-column format (Mfg_Part_Num, Part_Desc, E1_Brand,
Unilog_Brand, DIB_Brand, Part_Manuf). Add a file upload control to
App.jsx that posts to this endpoint, shows a loading state, and renders
all results using the existing ProductTable component. Show total count
and flagged_for_review count prominently above the results. Keep the
existing single-item form working alongside this.
```

## 2. Persist to Postgres
```
Add a SQLAlchemy model for EnrichedProduct in backend/app/db.py matching
models.py (store attributes as JSON). Wire main.py so /enrich and
/enrich/batch save results after generating them. Add GET /products
returning all saved products, most recent first. Use DATABASE_URL from
.env, create_all() on startup.
```

## 3. Human review queue view
```
Add GET /products/review-queue returning only needs_human_review=true
products. Add a second section in the frontend for this, visually
distinct (red-tinted header). This is a core part of the pitch - the
trust/validation layer the guide itself called out as valuable.
```

## 4. Prep for deploy
```
Add a Dockerfile for the backend (python:3.11-slim, install
requirements.txt, run uvicorn). Confirm `npm run build` works cleanly
for a static Vercel deploy of the frontend. Update vite.config.js proxy
to use an environment variable for the deployed backend URL in
production instead of localhost. Don't touch working logic.
```

---

## If you find the real reference files later

If `UNILOG_INTERNAL_CONTENT_GUIDELINES.docx`, `FAUCETS_LOV.xlsx`, or
`UniCat_Manufacturer_and_Brand_List.xlsx` surface (dashboard update,
support email reply, on-site at the hackathon):

```
I've obtained the real [FILENAME]. Here's its structure: [paste a sample
of rows/content]. Update app/data/[faucets_lov.py|manufacturers.py] to
use these real values instead of the hand-curated placeholder set, and
tell me if content_rules.py's formulas need adjusting to match the real
guidelines document's formulas.
```

This is a contained swap by design — only the data module changes, the
pipeline logic (retrieval, validation gate, confidence scoring,
description assembly) stays identical.

## Tips
- Always tell the agent what's already working before asking for more.
- Test each feature yourself before stacking the next prompt.
- Paste exact error messages, not "it doesn't work."
