# Faucets Enrichment & Trust Engine — UniHack (Unilog x Hack2Skill)

Scoped, per the Solution Guide's own advice ("depth beats breadth... one
category done fully... Faucets... is an excellent scope for a demo"), to
**one category done properly** rather than a shallow pass over all 1,000
sample rows or all 252 output columns.

## The honest disclosure (say this in your pitch, don't hide it)

The Solution Guide describes seven reference files (content guidelines,
Faucets LOV, UOM standards, manufacturer/brand master list, etc.) as the
rule book for correct output. **Only three files were ever actually
distributed via the dashboard**: the Solution Guide itself, the 1,000-row
sample input, and one worked example (a dishwasher). The other six —
including the two we need most, `UNILOG_INTERNAL_CONTENT_GUIDELINES.docx`
and `FAUCETS_LOV.xlsx` — are Unilog's proprietary internal data and were
never released to participants.

**No team has the real files.** So instead of pretending otherwise, this
build:
1. Hand-curates a defensible Faucets vocabulary (`app/data/faucets_lov.py`)
   from how real plumbing distributors (Ferguson, Build.com) structure
   attributes, plus real certification programs (WaterSense, cUPC, ADA).
2. Hand-curates a real manufacturer/brand list (`app/data/manufacturers.py`)
   — Moen, Delta, Kohler, American Standard, GROHE, Pfister, etc. — with
   correct legal names and ® symbols.
3. Reverse-engineers description formulas (`app/content_rules.py`) from the
   one worked example the guide does show, generalized to Faucets.
4. Architects every one of these as a **swappable, isolated module** — if
   the real files surface later (dashboard, email reply, or on-site at
   the hackathon), only these three files change. Nothing else in the
   pipeline needs touching.

Say exactly this in your deck. Judges built this challenge — they'll
recognize the constraint immediately, and showing you understood and
architected around it beats either ignoring it or building something
fragile on invented data without saying so.

## Architecture (the 3 stages we chose, per "pick 2-3 steps")

1. **Classification + normalization** — placeholder brand fields
   (`-- Unbranded --` etc.) stripped, manufacturer/brand matched against
   the curated master list (distributor's own field first, web search
   fallback), taxonomy fixed to `Plumbing & HVAC>Kitchen & Bath
   Fixtures>Faucets`.
2. **LOV-constrained attribute extraction** — Gemini extracts candidate
   values from the description + manufacturer-only sources; every value
   is then validated in plain Python against the Faucets LOV
   (`app/normalization.py`) — off-vocabulary values are dropped, not kept.
3. **Deterministic description assembly** — the four formats (Invoice,
   Mobile, Short, Long) are built by code from validated facts, with
   character limits (≤40 CAPS / 60-80) **enforced in code**, not hoped
   for from the LLM.

**Sourcing rule compliance**: retrieval runs in two phases
(`app/retrieval.py`) — an identity search that explicitly excludes
marketplaces/distributors (Amazon, Ferguson, Home Depot, etc.), then a
spec search restricted to the identified manufacturer's own domain only,
via Tavily's `include_domains`. This directly satisfies the guide's
"manufacturer's own site or documentation... marketplaces and distributor
sites are explicitly excluded" rule.

**Confidence scoring** now has a hard gate: an attribute with 3 supporting
sources that still isn't a valid LOV value scores LOW, full stop — see
`app/confidence.py`. This is the direct answer to "the output is
constrained, not creative... a fluent description made of invented values
scores zero."

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in GEMINI_API_KEY and TAVILY_API_KEY
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Testing — the sample dataset doesn't contain faucets

We checked: the provided 1,000-row `Sample-1000_Items.xlsx` (your uploaded
CSV) has **zero real faucet products** in it — it's general industrial
parts. Don't waste time hunting for faucet rows in it. Instead, test with
real faucet part numbers directly:

| Mfg_Part_Num | Part_Desc | Part_Manuf |
|---|---|---|
| 7594 | Moen 7594 Arbor Pulldown Kitchen Faucet | Moen Inc |
| 9178-AR-DST | Delta 9178-AR-DST Trinsic Single Handle Pull-Down | Delta Faucet Co |
| K-596-VS | Kohler K-596-VS Simplice Pull-Down Kitchen Faucet | Kohler Co |

These are real, well-documented products from major manufacturers, so
retrieval should find manufacturer-domain sources and you should see a mix
of HIGH/MEDIUM confidence, not everything defaulting to LOW. Try a made-up
or obscure part number too, to confirm it correctly flags `needs_human_review`.

## Evaluation — run this before the deck

```bash
# after testing a batch, save the response JSON, then:
python -m app.evaluation path/to/batch_response.json
```

Reports the three metrics the guide says judges look for: character-limit
compliance %, LOV-match %, and (if you obtain the real 200-item ground
truth) field-level accuracy. See `app/evaluation.py` docstring for how to
plug in the real ground truth file if it surfaces.

## What's intentionally NOT built yet

1. CSV batch upload wired into the frontend (backend endpoint `/enrich/upload-csv` already works — accepts the real 6-column format)
2. Persistence (Postgres/Supabase)
3. Review-queue UI view
4. Deploy config

See `PROMPTS.md`.

## Day-by-day (adjust as you go)

- **Now–Aug 15**: get this running, test the 3 real faucet part numbers above, run the evaluation script, confirm the numbers look defensible
- **Aug 16–20**: CSV batch flow, review queue, architecture diagram, deploy
- **Aug 21–22**: demo video, fill in the mandatory .pptx template
- **Aug 23 morning**: final cleanup, submit
