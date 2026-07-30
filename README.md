# Research Assistant Crew

A multi-agent research pipeline: give it a question, and five agents work
together to plan, search, extract claims, cross-check facts, and write a
sourced report with a confidence "verdict" on every claim.

```
Planner → Search Agent → Summarizer → Fact-Checker → Report Writer
              (parallel across sub-questions)
```

- **LLM**: [Groq](https://console.groq.com/keys) — free API key, no other paid services required.
- **Search**: DuckDuckGo (via the `ddgs` library) — free, no API key needed.
- **Backend**: FastAPI (Python), async pipeline, in-memory job queue.
- **Frontend**: React + Vite + Tailwind.

## Quick start

### 1. Backend

```bash
cd backend
cp .env.example .env       # then edit .env and paste your GROQ_API_KEY
./run.sh                   # creates a venv, installs deps, starts on :8000
```

Get a free Groq key at **https://console.groq.com/keys** (no credit card
required). Paste it into `backend/.env` as `GROQ_API_KEY=...`.

If you'd rather run it manually instead of `run.sh`:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your key
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                # starts on :5173
```

Open **http://localhost:5173**, type a research question, pick a depth and
audience, and submit.

## How it works

1. **Planner** breaks your question into 3–7 independently searchable
   sub-questions (count depends on the "depth" you pick).
2. **Search Agent** (running in parallel, one per sub-question) turns each
   sub-question into a search query, runs it against DuckDuckGo, filters out
   low-quality/duplicate domains, and fetches page text for the top results.
3. **Summarizer** extracts discrete, sourced claims from that text, and flags
   whether each claim is corroborated by multiple sources, single-sourced, or
   contradicted between sources.
4. **Fact-Checker** assigns every claim a verdict (`verified` / `plausible` /
   `unverified` / `contradicted`) and a confidence level, weighing source
   quality and cross-source agreement. Strongly corroborated, high-quality
   claims are fast-pathed without a model call to save on rate limits.
5. **Report Writer** synthesizes everything into a report with one section
   per sub-question, weaving in the verdict "stamps" you see rendered inline
   in the UI, plus a references list.

The frontend polls the backend every ~1.4s while a job runs, and shows live
progress through each of the five stages.

## Configuration

All tuning knobs live in `backend/.env` (copy from `.env.example`):

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Your free Groq key. Required. |
| `GROQ_MODEL` | Defaults to `openai/gpt-oss-120b` (Groq's current free-tier recommended model). |
| `GROQ_MAX_CONCURRENCY` | Caps simultaneous Groq calls to stay under free-tier rate limits. |
| `SEARCH_MAX_CONCURRENCY` | Caps simultaneous search/page-fetch requests. |
| `FRONTEND_ORIGIN` | CORS origin allowed to call the API. |

Research **depth** (chosen per-query in the UI, not in `.env`) controls how
many sub-questions are researched and how many sources are pulled per
sub-question — see `depth_presets` in `backend/app/config.py`.

## Notes on the free-tier setup

- Groq's free tier is rate-limited (requests/minute and tokens/minute vary by
  model). The pipeline batches and retries with backoff, and fast-paths
  obviously-solid claims to conserve calls, but very "deep" research on a
  broad topic can still take a couple of minutes or occasionally hit a
  rate limit and retry.
- Groq periodically deprecates older models. If `GROQ_MODEL` in your `.env`
  stops working, check https://console.groq.com/docs/deprecations for the
  current recommended replacement and swap it in — no code changes needed.
- DuckDuckGo search has no official API and can occasionally rate-limit or
  block automated queries. If searches start failing, wait a bit or reduce
  `SEARCH_MAX_CONCURRENCY`.
- This environment's build sandbox could not reach external hosts (Groq,
  DuckDuckGo) to run a full live end-to-end test — the pipeline was
  validated for correct wiring, graceful error handling, and clean startup,
  but you should run one real query yourself after adding your API key to
  confirm the live model output end-to-end.

## Project structure

```
backend/
  app/
    agents/            planner, search_agent, summarizer, fact_checker, report_writer
    main.py            FastAPI routes
    orchestrator.py     wires the agents together, parallel fan-out per sub-question
    groq_client.py      Groq API wrapper (JSON mode, retries, concurrency limit)
    search_tools.py      DuckDuckGo search + page-text fetching
    job_store.py         in-memory job/progress tracking
    schemas.py           Pydantic data contracts shared by every agent
    config.py            env-driven settings + depth presets
  requirements.txt
  run.sh
frontend/
  src/
    components/         QueryForm, PipelineRail, ReportView, VerdictStamp, ReferenceList, InlineClaims
    App.jsx              polling + page flow
    api.js                fetch client
  tailwind.config.js
```
