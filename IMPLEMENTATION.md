# Research Assistant Crew — Implementation Documentation

A full-stack, multi-agent research application. A user submits a question;
five specialized agents collaborate — planning, searching, summarizing,
fact-checking, and writing — to produce a structured, sourced report where
every claim carries a visible confidence verdict.

This document describes what the system does, how it is built, and why each
part exists.

---

## 1. Product Overview

### 1.1 What it does

The user types a research question into a web UI, chooses a **depth**
(Quick / Standard / Deep) and a target **audience** (General / Technical /
Executive), and submits. The system then:

1. Breaks the question into several independently-searchable sub-questions.
2. Searches the web for each sub-question in parallel.
3. Extracts discrete factual claims from the retrieved sources.
4. Cross-checks every claim and assigns it a verdict and confidence level.
5. Synthesizes everything into a final report, with inline citations and a
   references list.

The user watches this happen live via a progress rail, then receives a
report styled as a "case file" — each claim in the prose is annotated with a
colored, rotated "stamp" (Verified / Plausible / Unverified / Contradicted)
that can be hovered for the fact-checker's reasoning.

### 1.2 Design goals

- **No paid dependencies.** The only external service is Groq's free-tier
  LLM API. Web search uses DuckDuckGo, which requires no API key.
- **Transparency over authority.** The system never states a claim more
  confidently than its evidence supports — every claim is explicitly labeled,
  never silently asserted.
- **Resilience on a free tier.** Rate limits, malformed model output, and
  flaky search results are all expected conditions, not edge cases — the
  pipeline degrades gracefully rather than crashing.
- **Live visibility.** The user always sees which stage is running, not just
  a spinner.

---

## 2. System Architecture

```
┌──────────────────────────┐        HTTP (poll every 1.4s)        ┌──────────────────────────┐
│   Frontend (React/Vite)  │ ────────────────────────────────────▶│   Backend (FastAPI)      │
│                          │◀──────────────────────────────────── │                          │
│  QueryForm → PipelineRail│        JSON job state                │  /api/research (POST)    │
│  → ReportView            │                                      │  /api/research/{id} (GET)│
└──────────────────────────┘                                      └────────────┬─────────────┘
                                                                                 │
                                                                                 ▼
                                                                   ┌─────────────────────────┐
                                                                   │      Orchestrator        │
                                                                   │  (async pipeline runner) │
                                                                   └────────────┬─────────────┘
                                                                                 │
                        ┌───────────────┬───────────────┬────────────┬──────────┴─────────┐
                        ▼               ▼               ▼            ▼                    ▼
                    Planner       Search Agent     Summarizer   Fact-Checker        Report Writer
                  (1 LLM call)   (N parallel:      (N parallel:  (1 batched         (1 LLM call,
                                 DDG search +        LLM call     LLM call for       synthesizes
                                 page fetch)         per sub-Q)   uncertain claims)  everything)
                        │               │               │            │                    │
                        └───────────────┴───────────────┴────────────┴────────────────────┘
                                                    │
                                           Groq API (LLM)      DuckDuckGo (search + pages)
```

**Request lifecycle:**

1. Frontend `POST /api/research` with `{ query, depth, audience }`.
2. Backend creates an in-memory `Job` record, returns it immediately with
   `status: "queued"`, and schedules `run_pipeline()` as a FastAPI background
   task (non-blocking — the HTTP request returns instantly).
3. Frontend polls `GET /api/research/{job_id}` every 1.4 seconds.
4. The orchestrator mutates the job's `stages` list as each agent starts and
   finishes, so every poll reflects live progress.
5. On completion, the job carries the full `FinalReport` object; on failure,
   it carries an `error` string and the stage that failed.

No database is used — job state lives in a process-local Python dict
(`JobStore`). This is intentional for a single-instance, free-tier deployment;
see §7 for how to swap in persistent storage.

---

## 3. Backend

**Stack:** Python 3.12, FastAPI, Pydantic v2, httpx (async HTTP), `ddgs`
(DuckDuckGo search), BeautifulSoup4 + lxml (HTML text extraction), tenacity
(retry/backoff), python-dotenv.

### 3.1 File map

```
backend/
  app/
    main.py              FastAPI app + 3 routes
    config.py            env-driven Settings singleton + depth presets
    schemas.py            every Pydantic data contract used across agents
    job_store.py          in-memory job/progress tracker
    groq_client.py         Groq API wrapper (JSON mode, retry, concurrency cap)
    search_tools.py        DuckDuckGo search + page-text fetch + domain scoring
    orchestrator.py         wires the 5 agents into one async pipeline
    agents/
      planner.py
      search_agent.py
      summarizer.py
      fact_checker.py
      report_writer.py
  requirements.txt
  run.sh                  one-shot venv + install + .env scaffold + serve
  .env.example
```

### 3.2 Configuration (`config.py`)

A single `Settings` object reads from environment variables (via
`python-dotenv`), with these knobs:

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | *(none)* | Required. Free key from console.groq.com. |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Any Groq-hosted chat model with JSON-mode support. |
| `GROQ_MAX_CONCURRENCY` | `3` | Caps simultaneous Groq calls (asyncio.Semaphore). |
| `SEARCH_MAX_CONCURRENCY` | `5` | Caps simultaneous search/page-fetch calls. |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS allow-list entry. |

`depth_presets` maps the three UI depth options to pipeline parameters:

| Depth | Sub-questions | Sources per sub-question |
|---|---|---|
| `quick` | 3 | 3 |
| `standard` | 5 | 4 |
| `deep` | 7 | 6 |

### 3.3 Data contracts (`schemas.py`)

Every value passed between agents, stored in the job store, or returned over
HTTP is a typed Pydantic model — nothing is passed around as loose dicts.
Key models:

- **`ResearchRequest`** — `query`, `depth` (enum), `audience` (enum).
- **`ResearchPlan`** — `main_query`, `restated_goal`, list of `SubQuestion`
  (`id`, `text`, `rationale`).
- **`SearchResult`** — one retrieved page: `source_id`, `sub_question_id`,
  `url`, `title`, `domain`, `source_type` (enum: news / reference / academic
  / official / blog_or_forum / other), `published`, `snippet`, `content`,
  `quality_score` (0–1 float).
- **`Claim`** — `claim_id`, `sub_question_id`, `text`, `source_ids`,
  `agreement` (enum: corroborated / single_source / contradicted).
- **`Verdict`** — `claim_id`, `verdict` (enum: verified / plausible /
  unverified / contradicted), `confidence` (enum: high / medium / low),
  `method`, `notes`.
- **`ReportSection`**, **`Reference`**, **`ReportStats`**, **`FinalReport`** —
  the assembled output.
- **`Stage`**, **`Job`** — pipeline progress and the full job envelope
  returned to the frontend.

Using enums + Pydantic validation everywhere means a malformed field from an
LLM response is caught and defaulted rather than silently corrupting
downstream state (see §3.6, defensive fallbacks).

### 3.4 Groq client (`groq_client.py`)

A thin async wrapper around Groq's OpenAI-compatible
`/openai/v1/chat/completions` endpoint. This is the **only** integration
point with the LLM — every agent calls through it, never `httpx` directly.

- `complete_json(system, user, temperature, reasoning_effort)` — requests
  `response_format: {"type": "json_object"}` and parses the result; raises
  `GroqError` with the raw text on invalid JSON so failures are diagnosable.
- `complete_text(...)` — same, without forcing JSON.
- **Concurrency cap**: an `asyncio.Semaphore(GROQ_MAX_CONCURRENCY)` wraps
  every call, so parallel sub-question processing doesn't blow through the
  free tier's rate limit.
- **Retry/backoff**: `tenacity` retries up to 4 times with exponential
  backoff (1.5s–20s) specifically on HTTP 429 (`RateLimited`), leaving other
  errors (auth, malformed request) to fail fast.
- **`reasoning_effort`**: only attached to the payload when `GROQ_MODEL`
  starts with `openai/gpt-oss` (the reasoning-model family), so switching to
  a different Groq model in `.env` never breaks the request shape. Set to
  `"low"` for simple extraction/formatting calls and `"medium"` for the
  Report Writer's synthesis call, trading a little latency for better prose
  on the hardest reasoning step in the pipeline.

### 3.5 Search tools (`search_tools.py`)

No API key required — uses the `ddgs` (DuckDuckGo) library plus direct HTML
fetching:

1. `web_search(query)` — runs `DDGS().text(...)` in a thread (it's a
   blocking library) and returns raw hits.
2. `fetch_page_text(url)` — fetches the page with an async `httpx` client
   (12s timeout, custom User-Agent), strips `script`/`style`/`nav`/`footer`/
   `header`/`aside`/`form` tags with BeautifulSoup, concatenates paragraph
   text, and truncates to 6000 characters.
3. `search_and_fetch(sub_question_id, query, max_results)` — the orchestration
   function: runs the search, **deduplicates by domain** (one hit per
   domain, so five URLs from the same news site don't crowd out variety),
   classifies each domain's `source_type`, assigns a `quality_score`, and
   fetches page bodies **in parallel** for the surviving candidates.

**Domain classification & quality scoring** is heuristic and rule-based (no
LLM call needed):
- `.edu`, arxiv.org, ncbi.nlm.nih.gov, jstor.org, nature.com,
  sciencedirect.com → `academic` (quality 0.92)
- `.gov`, `.int`, who.int, un.org → `official` (quality 0.95)
- Reuters, AP, BBC, NYT, WSJ, Bloomberg, Guardian, NPR, Economist, FT →
  `news` (quality 0.8)
- Wikipedia, Britannica → `reference` (quality 0.7)
- blog/medium/reddit/forum substrings → `blog_or_forum` (quality 0.35)
- A small blocklist (Pinterest, Quora, Yahoo Answers, Ask.com, SlideShare)
  is forced to quality 0.15 regardless of the above.
- Everything else → `other` (quality 0.55).

This quality score feeds directly into the Fact-Checker's verdicts (§3.6).

### 3.6 The five agents

All agent modules are pure async functions that take typed inputs and return
typed outputs — no shared mutable state, which is what makes the parallel
fan-out in the orchestrator safe.

**1. Planner** (`agents/planner.py`)
- One Groq call. System prompt instructs the model to produce concrete,
  independently searchable, non-overlapping sub-questions ordered from
  foundational to nuanced.
- Number of sub-questions requested is driven by the depth preset.
- **Defensive fallback**: if the model returns zero usable sub-questions,
  the pipeline falls back to a single sub-question equal to the original
  query, so the pipeline never dead-ends on a bad response.

**2. Search Agent** (`agents/search_agent.py`)
- Runs **once per sub-question, in parallel** (via `asyncio.gather` in the
  orchestrator — this is the main concurrency win in the pipeline).
- First makes a small Groq call to reformulate the sub-question into a
  concise (<12 words) search-engine-friendly query; falls back to the raw
  sub-question text if that call fails.
- Then calls `search_and_fetch` (§3.5) to get ranked, deduplicated,
  content-populated `SearchResult`s.

**3. Summarizer** (`agents/summarizer.py`)
- One Groq call per sub-question (parallel, alongside the search calls in
  the same fan-out).
- Given up to ~1500 characters of excerpt per source, extracts up to 6
  discrete, checkable claims, each tagged with the exact `source_id`s that
  support it and an `agreement` label (`corroborated` if 2+ sources agree,
  `single_source`, or `contradicted` if sources disagree — in which case
  both sides are emitted as separate claims).
- **Validation**: any claim referencing a `source_id` that wasn't actually
  in the input is dropped, and any unrecognized `agreement` value defaults
  to `single_source` — the model's output is never trusted blindly.

**4. Fact-Checker** (`agents/fact_checker.py`)
- Two-tier design to conserve free-tier rate limits:
  - **Fast path (no LLM call)**: a claim marked `corroborated` whose average
    source quality is ≥ 0.85 is automatically verdict `verified` /
    confidence `high` — multiple independent high-quality sources agreeing
    doesn't need a model's opinion.
  - **Model review (batched)**: every other claim (single-sourced,
    contradicted, or corroborated-but-low-quality) is sent to Groq in a
    **single batched call** — not one call per claim — with each claim's
    text, agreement type, and source domains/quality scores. The model
    returns a verdict, confidence, and one-sentence note for each.
- **Defensive fallback**: if the model skips a claim in its response, that
  claim defaults to `unverified` / `low confidence` rather than being
  silently dropped from the report.

**5. Report Writer** (`agents/report_writer.py`)
- One Groq call (medium reasoning effort — this is the hardest synthesis
  step). Given the plan, every claim, and every verdict, it writes:
  - A title and a 3–4 sentence executive summary.
  - One section per sub-question (2–4 sentences of synthesized prose, not a
    bullet list), with claim citations woven in inline as `[[claim_id]]`
    markers — the frontend renders these as verdict stamps.
  - Explicit instruction to **hedge language to match verdict confidence**
    (e.g., "reportedly" / "one source suggests" for plausible/unverified
    claims) — the writer is not allowed to launder an uncertain claim into
    confident prose.
- **Defensive fallback**: if the model call fails or returns no sections,
  the writer falls back to auto-generating one section per sub-question
  directly from the raw claim list, so a Report Writer failure never means
  an empty report.
- Also assembles the deduplicated `references` list (one entry per source
  actually cited by a claim) and `ReportStats` (sub-question count, sources
  consulted, claims extracted/verified/contradicted, elapsed seconds).

### 3.7 Orchestrator (`orchestrator.py`)

Coordinates the five agents in order, with the middle stage parallelized:

```
Planner (await)
   │
   ▼
asyncio.gather( Search+Summarize for sub-Q 1, sub-Q 2, ... sub-Q N )   ← parallel fan-out
   │
   ▼
Fact-Checker (await, batched)
   │
   ▼
Report Writer (await)
```

Before/after each stage, `job_store.set_stage(...)` updates that stage's
status (`pending` → `running` → `done`/`error`) and a human-readable detail
string (e.g. `"5 sub-questions identified"`, `"18 sources retrieved"`,
`"4/7 claims verified"`) — this is exactly what the frontend's progress rail
displays.

**Error handling**: the entire pipeline body is wrapped in one `try/except`.
On any exception, the orchestrator identifies whichever stage was marked
`running` and marks the job `failed` with the exception message attached —
so a Groq auth error, a search timeout, or a JSON-parsing failure all surface
as a specific, readable error in the UI rather than a silent hang.

### 3.8 Job store (`job_store.py`)

A minimal in-memory store: a Python dict keyed by a 12-character hex job ID
(`uuid.uuid4().hex[:12]`). Exposes `create`, `get`, `set_stage`, `fail`, and
`complete`. `PIPELINE_STAGES` is the canonical ordered list of the 5 stages
with their display labels, used to initialize every new job.

### 3.9 API surface (`main.py`)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Returns `{status, groq_key_configured}` — used by the frontend and for manual debugging. |
| `POST` | `/api/research` | Body: `ResearchRequest`. Creates a job, schedules the pipeline as a background task, returns the job immediately (status `queued`). |
| `GET` | `/api/research/{job_id}` | Returns the current `Job` state (stages, plan once available, report once complete, error if failed). Polled by the frontend. |

CORS is configured to allow the configured `FRONTEND_ORIGIN` plus
`localhost:5173` / `127.0.0.1:5173` by default.

---

## 4. Frontend

**Stack:** React 19, Vite, Tailwind CSS 3 (utility classes + a handful of
custom CSS utilities for effects Tailwind can't express directly, e.g.
backdrop blur combined with gradient borders).

### 4.1 File map

```
frontend/
  src/
    main.jsx                  React root
    App.jsx                    page flow: intake → progress → report
    api.js                     fetch wrapper (startResearch, getJob, checkHealth)
    index.css                   global theme, aurora background, gradient/glass utilities
    components/
      QueryForm.jsx             the intake card (query, depth, audience, submit)
      PipelineRail.jsx           live 5-stage vertical progress ledger
      ReportView.jsx             final report card (title, summary, stats, sections, references)
      InlineClaims.jsx           parses [[claim_id]] markers into VerdictStamp components
      VerdictStamp.jsx           the rotated verdict "stamp" badge + hover tooltip
      ReferenceList.jsx          numbered source list at the bottom of the report
  tailwind.config.js            design tokens (colors, shadows, keyframes, animations)
  index.html
```

### 4.2 Application flow (`App.jsx`)

Single-page, three-phase flow driven by one `job` state object:

1. **Intake** (`job === null`): renders `<QueryForm>`.
2. **In progress** (`job` exists, not yet complete/failed): renders a
   two-column layout — a sticky `<PipelineRail>` on the left showing the 5
   stages, and on the right the original query plus (once available) the
   Planner's sub-questions with their rationales, streamed in as soon as
   that stage finishes (the user doesn't wait for the whole pipeline to see
   the plan).
3. **Complete** (`job.status === "complete"`): renders `<ReportView>`.

**Polling mechanics**: on submit, `startResearch()` POSTs the request and
immediately gets back a queued job. A `setInterval` then calls `getJob(id)`
every 1400ms, replacing the `job` state each time, until `status` is
`"complete"` or `"failed"`, at which point the interval is cleared. The
interval is also cleaned up on component unmount and on "New research" reset.

**Failure state**: shown inline with the raw error message from the backend
and a "Try again" link that resets to the intake screen.

### 4.3 Components

- **`QueryForm.jsx`** — the entire intake experience:
  - A `textarea` for the question, with animated corner brackets that
    highlight on focus.
  - Two independent, full-width option groups (**Depth**: Quick/Standard/Deep
    with thread-count hints; **Report for**: General/Technical/Executive),
    each a `flex flex-wrap` row of pill buttons — deliberately *not* a
    two-column grid, so that wrapping in one group never misaligns against
    the other.
  - A gradient-bordered glass card wrapping the whole form, with a small
    decorative "wax seal" emblem in the corner.
  - A gradient submit button with a hover shimmer sweep and an arrow that
    slides on hover.
  - Local state only (`query`, `depth`, `audience`, `focused`); calls
    `onSubmit({ query, depth, audience })` — no API calls happen inside this
    component.

- **`PipelineRail.jsx`** — renders the 5 pipeline stages as a vertical,
  connected ledger. Each stage shows an icon reflecting its status:
  hollow dot (pending), pulsing amber dot (running), green check (done), or
  red X (error) — plus the stage's live `detail` string once available.

- **`ReportView.jsx`** — the final deliverable, rendered as a light "paper"
  card floating on the dark shell (a deliberate contrast: the app chrome is
  dark/atmospheric, the report itself reads like a printed document):
  - Title, executive summary.
  - A stats strip (threads / sources / claims / verified / contested /
    seconds) pulled straight from `ReportStats`.
  - One section per sub-question, with claim citations rendered inline via
    `<InlineClaims>`.
  - A references list via `<ReferenceList>`.
  - A **"Download .md"** button that client-side converts the report to a
    plain Markdown file (stripping the `[[claim_id]]` markers) and triggers
    a browser download — no server round-trip needed.
  - A **"New research"** button that resets `App`'s state back to intake.

- **`InlineClaims.jsx`** — a small regex-based renderer: scans a section's
  body text for `[[claim_id]]` tokens, and replaces each with a
  `<VerdictStamp>` looked up from a `claim_id → Verdict` map, preserving all
  the surrounding prose text around it.

- **`VerdictStamp.jsx`** — the signature visual element. A small, rotated
  (-2°), monospace, uppercase badge colored per verdict (green ✓ Verified,
  amber ~ Plausible, slate ? Unverified, rose × Contradicted), with the
  confidence level appended, and a hover tooltip showing the Fact-Checker's
  one-sentence note. Includes a staggered pop-in animation so multiple
  stamps in a section don't all animate simultaneously.

- **`ReferenceList.jsx`** — a numbered list of every source actually cited
  by at least one claim, each linking out to the original URL with its
  domain and source-type label, styled to sit correctly on the report's
  light paper background (a separate, hand-tuned dark-on-light color set
  from the rest of the app's dark theme).

### 4.4 Visual design system

The UI follows a "case file lit by aurora light" concept — an
investigative/evidentiary aesthetic (research, sourcing, verdicts) combined
with a deliberately vivid, non-flat atmosphere:

- **Typography**: Fraunces (serif, display/headings — the "case file"
  voice), IBM Plex Sans (UI body text), IBM Plex Mono (stage labels, claim
  IDs, stamps, domains — the "evidentiary" register).
- **Color tokens** (`tailwind.config.js`, reused by every component):
  - Base surfaces: `ink`, `panel`, `panel2`, `rule` — deep indigo, not flat
    gray-black.
  - Report surface: `paper`, `paper-dim` — warm parchment, intentionally
    distinct from the app shell.
  - Text: `ash` (muted lavender-gray), `bone` (warm off-white).
  - **Verdict semantics** (used consistently everywhere a verdict appears):
    `verified` (emerald), `plausible` (amber/gold), `unverified`
    (slate-blue), `contradicted` (rose).
  - **Atmosphere accents**: `mystic` (violet), `bloom` (magenta), `glow`
    (cyan) — used for the aurora background, gradient text, and gradient
    borders, kept separate from the verdict palette so the two systems never
    collide semantically.
- **Background**: a fixed-position `.aurora` layer — two large, blurred,
  multi-color radial-gradient blobs that drift slowly (16–19s loops via CSS
  keyframes), plus a subtle film-grain texture (`.grain`, SVG `feTurbulence`)
  and an inset vignette (`.vignette`) to keep foreground text readable.
  Respects `prefers-reduced-motion` (all animation durations collapse to
  ~0ms).
- **Signature motifs**:
  - The **verdict stamp** (rotated, monospace, color-coded badge) — reused
    identically in the report body.
  - The **wax-seal emblem** on the intake card — ties the "case file" framing
    to a tactile, almost magical object.
  - **Gradient-bordered glass cards** (`.gradient-border` + `.glass-card`
    utility classes) — a padding-trick gradient background with an inset
    semi-transparent, backdrop-blurred panel, used for the intake form.
  - **Gradient text** (`.gradient-text`) for the main headline, animated to
    slowly pan across the amber→magenta→violet stops.

Because every component pulls its colors from the same named Tailwind tokens
rather than hardcoded hex values, the entire app's palette can be re-themed
by editing `tailwind.config.js` alone.

---

## 5. End-to-End Data Flow (Worked Example)

1. User submits `"What causes coral bleaching?"`, depth `standard`,
   audience `general`.
2. Backend creates job `a1b2c3d4e5f6`, returns it with all 5 stages
   `pending`.
3. **Planner** runs → `ResearchPlan` with 5 sub-questions, e.g. *"What is
   the biological mechanism of coral bleaching?"*, *"What ocean temperature
   thresholds trigger bleaching?"*, etc. Stage marked done:
   `"5 sub-questions identified"`.
4. **Search + Summarize** run in parallel, one pair per sub-question:
   - Each sub-question's search query is generated, DuckDuckGo is queried,
     duplicate domains are dropped, ~4 pages are fetched and scored.
   - Each sub-question's claims are extracted from that sub-question's own
     sources only.
   - Stage marked done once all 5 pairs resolve:
     `"19 sources retrieved"` / `"14 claims extracted"`.
5. **Fact-Checker** runs once over all 14 claims: some fast-pathed to
   `verified` (e.g. a claim corroborated by NOAA + a peer-reviewed paper),
   the rest sent in one batched Groq call. Stage marked done:
   `"9/14 claims verified"`.
6. **Report Writer** runs once, producing a title, executive summary, 5
   sections (one per sub-question) with `[[claim_id]]` markers woven in, and
   a deduplicated reference list. Stage marked done: `"Report ready"`.
7. Job marked `complete`; frontend's next poll receives the full report and
   switches to `<ReportView>`.

---

## 6. Error Handling & Resilience

| Failure mode | Behavior |
|---|---|
| No `GROQ_API_KEY` set | Planner call raises immediately with a clear message; job fails at the `planner` stage with that message shown in the UI. |
| Groq rate limit (HTTP 429) | Retried up to 4× with exponential backoff (1.5s–20s) before surfacing as a failure. |
| Malformed/non-JSON model response | Raises `GroqError` with the raw text included, so the failure is diagnosable from logs; individual agents also apply field-level validation and drop/default bad values rather than propagating `None`s. |
| Planner returns 0 sub-questions | Falls back to a single sub-question equal to the raw query. |
| A search/page-fetch fails for one source | That source is silently skipped (`fetch_page_text` returns `""` on any exception); the pipeline never fails because of one bad URL. |
| Summarizer/Fact-Checker/Report-Writer call fails outright | Each has its own defensive fallback (empty claim list / all-unverified defaults / claim-list-derived minimal report, respectively) so a single failed call degrades the *quality* of the report rather than crashing the whole job. |
| Frontend loses connection mid-poll | Polling stops, the raw error message is shown with a way to reset and retry. |

---

## 7. Known Limitations & Extension Points

- **In-memory job store**: jobs are lost on backend restart, and this
  design doesn't scale past a single process. For production/multi-instance
  use, swap `JobStore` for Redis or a database-backed equivalent — the
  interface (`create`/`get`/`set_stage`/`fail`/`complete`) is small and
  isolated in one file.
- **Polling, not push**: the frontend polls every 1.4s rather than using
  WebSockets/SSE. Simple and robust, but adds up to ~1.4s of latency to
  perceived stage transitions. Could be upgraded to Server-Sent Events
  without changing the agent/orchestrator code at all.
- **DuckDuckGo has no official API** and can occasionally rate-limit or
  block automated queries; `SEARCH_MAX_CONCURRENCY` exists specifically to
  reduce that risk.
- **Groq model deprecation**: Groq periodically retires older models (the
  original default, `llama-3.3-70b-versatile`, was deprecated in favor of
  `openai/gpt-oss-120b` during this project's development). `GROQ_MODEL` is
  a single env var specifically so this doesn't require a code change.
- **No authentication/multi-tenancy**: this is a single-user local tool as
  built; there's no concept of accounts, saved history, or per-user job
  isolation.
- **No automated test suite** is included; validation so far has been
  manual (endpoint smoke tests, import checks, a full frontend production
  build). See the note in the README about running one real end-to-end
  query yourself with a live Groq key.

---

## 8. Tech Stack Summary

| Layer | Technology |
|---|---|
| LLM provider | Groq (`openai/gpt-oss-120b`, free tier) |
| Web search | DuckDuckGo via `ddgs` (no key required) |
| Backend framework | FastAPI + Uvicorn |
| Backend language | Python 3.12 |
| Data validation | Pydantic v2 |
| HTTP client | httpx (async) |
| HTML parsing | BeautifulSoup4 + lxml |
| Retry/backoff | tenacity |
| Frontend framework | React 19 |
| Build tool | Vite |
| Styling | Tailwind CSS 3 + custom CSS utilities |
| Fonts | Fraunces, IBM Plex Sans, IBM Plex Mono (Google Fonts) |
