# Folio AI Portfolio Analyzer — Implementation Plan & Work Log

**Purpose:** this document is the durable plan + progress tracker for adding the LLM
portfolio analyzer to Folio. If the session is interrupted, resume from the
"Status Tracker" section below. It implements a scoped slice of
`Folio_AI_Portfolio_Advisor_Implementation_Plan.md` (the 105-section vision doc,
referred to below as "the vision plan"); section numbers (§n) refer to that document.

**Agreed iteration scope (confirmed with user):**

- AI analysis only, on demand, using existing holdings data + live yfinance data.
  No news pipeline, no transactions table, no price-history persistence, no
  scheduled/periodic analysis.
- Provider-agnostic LLM layer supporting **both OpenAI-compatible and Gemini**,
  selectable via env. MockProvider for offline dev/tests.
- yfinance as sole market/fundamental data source for now (wrapped in provider
  abstractions so better sources can slot in later per §9/§10/§91).
- Execution: FastAPI `BackgroundTasks` + polling via `GET /analysis/{run_id}` (no queue).
- Frontend: stock detail page with Analyze flow + portfolio AI summary page.
- Schema: minimal new tables (`analysis_runs`, `recommendations`,
  `investment_profiles`). Existing tables untouched. No transactions/thesis
  tables yet.
- Verification with MockProvider only (user has no API keys configured for smoke tests).

---

## 1. Architecture Overview

```
POST /analysis/holding/{id}  or  POST /analysis/portfolio
        │ (BackgroundTasks)
        ▼
AnalysisRun row (status CREATED → stage transitions → COMPLETED/FAILED/PARTIAL_COMPLETION)
        │
        ▼
Orchestrator (app/services/analysis/orchestrator.py)
  1. Gather data:
     - position/holdings (DB)
     - LTP + daily OHLCV      → market_data provider (yfinance)
     - fundamentals            → fundamentals provider (yfinance, TTL cache)
     - technicals              → deterministic computation from OHLCV
     - investment profile      → DB
  2. Build evidence pack (E-xxx ids, value, unit, source, observed_at,
     freshness, confidence) + data quality score (§53 subset)
  3. Run LLM agent stages (each: prompt file + evidence JSON → structured JSON):
     a. Fundamental Analyst  (per stock)
     b. Technical Analyst    (per stock)
     c. Portfolio Analyst    (once, whole portfolio context)
     d. Investment Committee (per stock, receives agent outputs a–c;
        produces final recommendation per §41 schema)
  4. Validate + persist Recommendation rows; update run status.
Frontend polls GET /analysis/{run_id} until terminal state, then
GET /analysis/latest/... to render.
```

Key principles enforced end-to-end (from vision plan):

- Evidence-first: LLM only reasons over evidence supplied; never invents facts (§40, §52).
- Facts carry source + observed_at metadata (§7, §8); prompt shows freshness.
- Portfolio layer can override security layer (§3): committee agent receives
  concentration verdict and must respect it.
- Recommendation taxonomy §31 with UI grouping BUY/HOLD/REDUCE/EXIT.
- Confidence ≠ probability of profit (§42); UI labels it "analysis confidence".
- Anti-bias rules (§83–85): no price anchoring on avg cost, no loss aversion,
  fresh-capital test.
- Conditional output: action + why + change-conditions + risk triggers (§32).
- Bull/base/bear + thesis validity + evidence citations in every result (§48, §41).

---

## 2. Backend

### 2.1 New DB models (`app/models.py`, appended)

**AnalysisRun**
```
id            UUID PK
user_id       UUID FK users, indexed
kind          VARCHAR(20)      # "holding" | "portfolio"
holding_id    UUID FK holdings, nullable (set when kind="holding")
status        VARCHAR(30)      # CREATED, RUNNING, COMPLETED, PARTIAL_COMPLETION, FAILED
stage         VARCHAR(40)      # current stage label (§72 subset), nullable
provider      VARCHAR(40)      # llm provider id (openai|gemini|mock)
model_name    VARCHAR(100), nullable
prompt_version VARCHAR(20)     # e.g. "v1"
error_message TEXT, nullable
started_at    TIMESTAMP nullable
completed_at  TIMESTAMP nullable
created_at    TIMESTAMP
```

**Recommendation**
```
id               UUID PK
run_id           UUID FK analysis_runs, indexed
user_id          UUID FK users, indexed
holding_id       UUID FK holdings, indexed (nullable; NULL on the portfolio-level row)
kind             VARCHAR(20)   # "holding" | "portfolio"
symbol           VARCHAR(40)
rating           VARCHAR(30)   # grouped: BUY | HOLD | REDUCE | EXIT (UI badge)
action           VARCHAR(40)   # detailed §31 action, e.g. HOLD_WAIT_FOR_CORRECTION
confidence       INTEGER 0–100, nullable
scores           JSON          # {business_quality, fundamental, valuation,
                               #  technical, portfolio_fit} — nullable fields allowed
thesis_status    VARCHAR(30), nullable   # VALID | STRENGTHENING | WEAKENING | INVALIDATED | UNKNOWN
summary          TEXT
why              TEXT, nullable
bull_case        TEXT, nullable
base_case        TEXT, nullable
bear_case        TEXT, nullable
key_reasons      JSON (list[str])
key_risks        JSON (list[str])
buy_conditions   JSON (list[str])
reduce_conditions JSON (list[str])
exit_conditions  JSON (list[str])
support_levels   JSON (list[float])
resistance_levels JSON (list[float])
fair_value_range JSON {"low":..,"base":..,"high":..} nullable values
evidence_ids     JSON (list[str])
data_quality     VARCHAR(20)   # EXCELLENT | GOOD | MODERATE | POOR
quality_flags    JSON (list[str])  # e.g. LOW_CONFIDENCE, STALE_DATA, PORTFOLIO_CONCENTRATION (§44)
health_score     INTEGER nullable    # portfolio-level only (§58)
positives        JSON (list[str])    # portfolio-level only
concerns         JSON (list[str])    # portfolio-level only
priority_note    TEXT nullable       # portfolio-level only
analysis_timestamps JSON nullable    # {generated_at, market_data_through, note} (§54)
created_at       TIMESTAMP
```

**InvestmentProfile**
```
user_id                     UUID PK/FK users
investment_style            VARCHAR(30) default "Moderate"   §4
risk_tolerance              VARCHAR(20) default "Medium"     # Low|Medium|High|Very High
investment_horizon          VARCHAR(30) default "Medium term: 6-24 months"
max_single_stock_weight     FLOAT default 15.0    # percent, §27 default high-risk bound
max_sector_weight           FLOAT default 35.0    # percent
warn_single_stock_weight    FLOAT default 10.0
warn_sector_weight          FLOAT default 25.0
updated_at                  TIMESTAMP
```
Profile is user-scoped, auto-created with defaults on first read when missing.

### 2.2 LLM provider layer (`app/services/llm/`)

Files:
- `base.py` — `LLMProvider` ABC:
  ```python
  class LLMProvider(ABC):
      provider_id: str
      model_name: str
      async def generate_json(self, system: str, user: str,
                              temperature: float = 0.2,
                              max_tokens: int = 2048) -> dict
  ```
  Contract: returns parsed JSON dict. Base class implements `extract_json()`
  helper: try `json.loads`, strip ```json fences, else locate first `{`/last `}`.
  Retries up to 2x with instruction "respond with JSON only". Raises
  `LLMProviderError` on parse/HTTP failure.
- `openai_provider.py` — OpenAI-compatible adapter using **raw httpx**
  (avoid adding `openai` SDK dependency; works with any base URL):
  env: `OPENAI_API_KEY`, `OPENAI_BASE_URL` (default `https://api.openai.com/v1`),
  `OPENAI_MODEL` (default `gpt-4o-mini`). Uses `response_format={"type":"json_object"}`
  when `OPENAI_JSON_MODE != "false"`.
- `gemini_provider.py` — Gemini adapter using **raw httpx** against
  `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`:
  env: `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.0-flash`),
  `generationConfig.responseMimeType = "application/json"`.
- `mock_provider.py` — deterministic offline provider: inspects the prompt for
  the agent marker (e.g. `<<AGENT:fundamental>>`) and returns schema-valid
  canned JSON per agent. Scores derived loosely from evidence flags passed in
  (keeps tests realistic). Provider id "mock".
- `registry.py` — `get_llm_provider() -> LLMProvider` driven by
  `settings.llm_provider` ∈ {openai, gemini, mock}; raises config error with
  clear message when key missing.

### 2.3 Market data layer (`app/services/market_data/`)

Files:
- `base.py` — `MarketDataProvider` ABC: `get_ltp(symbol) -> float`,
  `get_ohlcv(symbol, period="1y") -> list[OHLCV]` (OHLCV = dataclass/pydantic:
  date, open, high, low, close, volume).
- `yfinance_provider.py` — normalizes `.NS`/`.BO` suffix like existing
  `backend/yfinance_service.py`; uses `yf.Ticker(...).history(period="1y")`
  for OHLCV; runs blocking calls in a thread (called from async context via
  `asyncio.to_thread`).

Existing `yfinance_service.py` stays for the existing LTP endpoints (no behavior change).

### 2.4 Fundamentals layer (`app/services/fundamentals/`)

Files:
- `base.py` — `FundamentalsProvider` ABC: `get_snapshot(symbol) -> FundamentalsSnapshot`
- `yfinance_provider.py` — builds normalized snapshot from `ticker.info`
  (+ `ticker.quarterly_financials` where cheap/reliable):
  - identity: company_name, sector, industry, market_cap, market_cap_category
    (cap buckets: large > ₹75,000cr etc. using info `marketCap` USD→INR approx,
    or skip category if ambiguous)
  - valuation: pe_trailing, pe_forward, pb, ev_to_ebitda, dividend_yield, peg (optional)
  - profitability: roe, roe (net profit margin), operating_margin, roce
    (approx: ebit / (total assets - current liabilities) when computable)
  - growth: revenue_growth (yoy, from info), earnings_growth (yoy)
  - balance sheet: debt_to_equity, current_ratio, total_cash, total_debt
  - cashflow: free_cashflow, operating_cashflow (info)
  - price context embedded in snapshot: fifty_two_week_high/low, beta
  - Every field optional (None when absent); provider tag + `observed_at`
    stamped on the snapshot. Units normalized (amounts in raw currency with
    unit marker "currency" since yfinance reports market cap in currency units;
    document in evidence builder — do not present ambiguous units to LLM §93).
- `cache.py` — module-level TTL cache keyed on symbol
  (default TTL 6h, setting `FUNDAMENTALS_CACHE_TTL_SECONDS`), so repeated
  analyses and portfolio-wide runs reuse data. Thread-safe via lock.

### 2.5 Technicals computation (`app/services/technicals/indicators.py`)

Pure functions on OHLCV list (newest-last):
- `ema(values, span)`, `sma(values, span)`
- `rsi(closes, period=14)` — Wilder smoothing
- `macd(closes)` → (macd_line, signal_line, histogram) latest values
- `atr(bars, period=14)` — Wilder
- `support_resistance(bars, window=20)` → recent swing low/high zones
- `drawdown_from_52w_high(closes)`
- `build_technical_snapshot(bars) -> TechnicalSnapshot` (pydantic):
  ema20/50/200, rsi14, macd histogram + direction, atr14, support/resistance
  zones, 52w high/low, distance % to each, volume trend (latest 20d avg vs
  prior 60d avg), trend states:
  - LONG_TERM_TREND: BULL/BEAR/NEUTRAL from close vs ema200 (+ ema50 vs ema200)
  - MEDIUM_TERM_TREND: close vs ema50
  - SHORT_TERM_TREND: close vs ema20
  - MOMENTUM: RSI bands (oversold <30, neutral, overbought >70)
  - VOLATILITY: atr% of price bands
  - OVERALL_TREND_SCORE 0–100 (weighted tally; deterministic, documented formula)
- Requires ≥ 60 bars; if insufficient, returns snapshot with
  `insufficient_data=True` and nulls (quality gate LOW_CONFIDENCE).

### 2.6 Evidence pack (`app/services/analysis/evidence.py`)

- `EvidenceItem` pydantic: `id` ("E001"…), `category` (position|market|
  fundamental|valuation|technical|portfolio), `label`, `value`, `unit`,
  `source` (user-input | yfinance | computed), `observed_at` (iso),
  `freshness` (FRESH/RECENT/STALE/unknown — based on observed_at vs now),
  `confidence` (HIGH/MEDIUM/LOW), `note` optional.
- Builders:
  - position evidence: qty, avg price, invested, LTP, current value, P/L abs/%,
    portfolio weight, distance to avg/SL/target (§26).
  - market/technical evidence from TechnicalSnapshot.
  - fundamental + valuation evidence from FundamentalsSnapshot.
  - portfolio context: total value, holding count, sector weights,
    concentration flags vs profile limits (§27), diversification notes.
- `build_evidence_pack(holding, holdings, technical, fundamental, profile)`
  → dict matching §40 package shape:
  `{security, position, fundamentals, valuation, technical, portfolio_context,
    investment_profile, evidence[], data_quality{}`
- `data_quality` (§53 subset): completeness % (non-null fundamentals fields),
  recency (freshness of LTP/technical), source coverage (yfinance single source
  ⇒ cap primary-source score), → score 0–100 and EXCELLENT/GOOD/MODERATE/POOR,
  plus list of quality gates triggered (§44): LOW_CONFIDENCE, STALE_DATA,
  LOW_SOURCE_CONFIDENCE, PORTFOLIO_CONCENTRATION. MIXED_SIGNAL deferred (needs
  multi-source). Every gate decision stored on the recommendation row.

### 2.7 Orchestration (`app/services/analysis/orchestrator.py`)

- `run_holding_analysis(db_factory, run_id, holding_id)` — stages:
  FETCHING_MARKET_DATA → FETCHING_FUNDAMENTALS → PROCESSING_TECHNICALS →
  BUILDING_EVIDENCE → ANALYZING_STOCK (fundamental agent, technical agent) →
  PORTFOLIO_CONTEXT (portfolio agent) → FINAL_RECONCILIATION (committee) →
  COMPLETED. Updates run.status/stage between stages with a fresh DB session
  (sessionmaker; do not reuse request session after response returns).
- `run_portfolio_analysis(...)` — for each holding: data gather + technicals
  (fundamentals fetched with cache reuse) + per-stock agents; one portfolio
  agent pass; committee pass per holding; then committee produces
  portfolio-level summary (health score 0–100, positives, concerns, priority,
  per-stock grouped actions). Persists N holding recommendations + 1 portfolio
  recommendation. On per-stock failure, mark run PARTIAL_COMPLETION, record
  reason, continue others (§72). Never silently fail.
- Guards in API layer: reject new run if the user has a non-terminal run
  (status CREATED/RUNNING); enforce `analysis.min_interval_seconds` (default 300)
  since last completed run of same kind (configurable).
- Concurrency: keep sequential per run (Render free tier); agents use
  `await provider.generate_json(...)`; blocking yfinance wrapped in
  `asyncio.to_thread`.
- Prompt rendering: `prompts.py` loads files from `app/prompts/` once (module
  cache), injects evidence JSON + profile + agent marker. Prompt files declare
  their version in a header comment.

### 2.8 Prompts (`app/prompts/*.md`, version `v1`)

Files (each with agent marker + explicit JSON output schema + rules):
- `fundamental_analyst_v1.md` — business quality, growth, profitability,
  debt, cash flow, valuation regime (§11–14), earnings quality flags (§12),
  output JSON: `{fundamental_score, business_quality_score, valuation_score,
  valuation_regime, earnings_quality, strengths[], concerns[], stale_data_notes[]}`.
- `technical_analyst_v1.md` — §24/§25 language; no naive RSI→SELL; output
  `{technical_score, trend_summary, momentum, entry_quality (GOOD_ENTRY|
  WAIT|POOR_ENTRY), support_levels[], resistance_levels[], notes}`.
- `portfolio_analyst_v1.md` — concentration vs limits, sector weights,
  position sizing verdict; output `{portfolio_fit_score, oversized_positions[],
  concentration_flags[], can_add_{symbol}_verdict}`-shaped context per stock.
- `final_investment_committee_v1.md` — §103 principles + §40 rules +
  §41 output schema. Includes: recommendation taxonomy (§31) mapping to UI
  group; conditional recommendations (§32); thesis_status; bull/base/bear;
  buy/reduce/exit conditions; fair_value_range (ranges, not false precision §13);
  confidence semantics (§42); anti-bias rules (§83–85); challenge-thesis (§81,
  §82 strongest bull/bear argument); null for unknowns (§52). Portfolio-mode
  variant (same file, mode flag in evidence): output §58/§59 shape
  `{health_score, positives[], concerns[], priority, stock_actions[]}`.

Prompt files embed the instruction: "Never invent facts, figures, news, targets
or sources. If data is missing, use null/unknown. Cite evidence IDs from the
evidence list for every material claim."

### 2.9 Schemas (`app/schemas.py`, appended) & router (`app/routers/analysis.py`)

Pydantic schemas (camelCase aliases to match frontend convention — check
existing `schemas.py` style and mirror it exactly):
- `AnalysisRunOut` — id, kind, holdingId, status, stage, provider, modelName,
  errorMessage, createdAt, startedAt, completedAt
- `RecommendationOut` — fields from §2.1 (camelCase)
- `InvestmentProfileIn/Out`

Endpoints (all JWT-protected, user-scoped):
```
POST /analysis/holding/{holding_id}   → 202 {run_id}   (BackgroundTasks)
POST /analysis/portfolio              → 202 {run_id}
GET  /analysis/{run_id}               → AnalysisRunOut (+ result recommendationIds)
GET  /analysis/latest/holding/{holding_id} → latest RecommendationOut or 404
GET  /analysis/latest/portfolio       → portfolio RecommendationOut + latest
                                        per-holding recommendations or 404
GET  /profile                         → InvestmentProfileOut
PUT  /profile                         → InvestmentProfileOut
```

### 2.10 Config (`app/config.py`)

```
llm_provider: str = "mock"            # openai | gemini | mock
openai_api_key: str = ""
openai_base_url: str = "https://api.openai.com/v1"
openai_model: str = "gpt-4o-mini"
gemini_api_key: str = ""
gemini_model: str = "gemini-2.0-flash"
llm_max_requests_per_minute: int = 15
llm_min_request_interval_seconds: float = 0.0
analysis_min_interval_seconds: int = 300
fundamentals_cache_ttl_seconds: int = 21600
```

### 2.11 Backend tests (`backend/tests/`)

Existing test layout unknown at plan time — inspect `backend/tests` first and
follow conventions. Planned tests (no network):
- `test_indicators.py` — EMA/SMA/RSI/MACD/ATR on synthetic series (known values).
- `test_evidence.py` — position/portfolio weight math, freshness states,
  data-quality score + gates (missing fundamentals → LOW_CONFIDENCE; weight >
  limit → PORTFOLIO_CONCENTRATION).
- `test_llm_json.py` — JSON extraction: clean JSON, fenced JSON, prose-wrapped JSON.
- `test_mock_provider.py` — mock provider returns schema-valid output for each agent.
- `test_analysis_api.py` — full flow with mock provider: register → holdings →
  POST holding analysis → poll to COMPLETED → latest recommendation has grouped
  rating in {BUY,HOLD,REDUCE,EXIT}, evidence ids, bull/base/bear; portfolio
  analysis produces portfolio row + per-stock rows; guard: second immediate run
  rejected 409; auth: other user cannot read run (404/403).

---

## 3. Frontend

### 3.1 Types (`src/lib/types.ts`)

- `InvestmentProfile`, `AnalysisRun`, `Recommendation` interfaces matching API
  (camelCase).
- `AnalysisRating = "BUY" | "HOLD" | "REDUCE" | "EXIT"`.

### 3.2 API client (`src/lib/api.ts`)

Extend `api` object:
```
startHoldingAnalysis(holdingId)  → { runId }
startPortfolioAnalysis()         → { runId }
getAnalysisRun(runId)            → AnalysisRun
getLatestHoldingAnalysis(holdingId) → Recommendation | null (catch 404 → null)
getLatestPortfolioAnalysis()     → { portfolio: Recommendation | null,
                                     holdings: Recommendation[] } | null
getProfile() / updateProfile(input) → InvestmentProfile
```
Polling helper `pollRun(runId, onStage, timeoutMs ≈ 120000, interval 2s)`.

### 3.3 Stock detail page — `src/app/holdings/[id]/page.tsx` (new; follow existing
app-shell + page patterns in `portfolio/page.tsx`)

Sections (§61 subset):
1. Company header: symbol, sector, broker, back link.
2. Position summary: qty, avg, LTP, invested, value, P/L abs+%, weight, SL/target.
3. AI recommendation card (§62): grouped rating badge, detailed action label,
   confidence bar ("Analysis confidence" wording, §42), thesis status pill,
   data-quality pill + quality flags, model/provider + generated-at timestamp (§54).
4. Why (§64 five-question block: recommendation / why / evidence / what could
   make it wrong / what to watch).
5. Bull / Base / Bear cards.
6. Key risks + buy/reduce/exit conditions.
7. Fair-value range vs current LTP vs user target (§36 comparison note).
8. Evidence panel: expandable list of evidence items used (id, label, value,
   source, observed_at, freshness).
9. Analyze button: disabled while a run is active; shows stage progress text
   from polling; on terminal state fetches latest and renders. Shows latest
   existing recommendation on page load if present.
10. Disclaimer footer: "AI analysis is decision-support, based on data as of the
    timestamps shown; not investment advice or a guarantee of returns."

### 3.4 Portfolio AI page — `src/app/ai/page.tsx`

1. Header + "Analyze portfolio" button (same run/poll UX as detail page).
2. Health score card (§58): score badge + status.
3. Positive / Concerns / Priority sections (§59).
4. Per-stock actions table: symbol, weight, grouped action badge, detailed
   action, confidence, link to detail page.
5. Analysis timestamp block + data-quality + model info (§54).
6. Portfolio weight concentration callouts from quality flags.

### 3.5 Integration with existing pages

- Holdings table (`portfolio/page.tsx` / `holdings-table.tsx`): add per-row
  "View" link to detail page; AI View column only if latest per-stock analysis
  exists (fetched via latest/portfolio endpoint; render pill or "—"). Keep
  existing Fetch/Refresh behavior unchanged.
- Nav (`app-shell.tsx`): add "AI Advisor" link.

### 3.6 UI conventions

Follow existing component patterns (`status-pill`, `button`, `skeleton`,
`kpi-card`), existing format helpers (`format.ts`, INR formatting), existing
dark styling/layout. Responsive: cards stack on mobile; tables scroll.
No new chart dependencies this iteration (score bars via pure CSS width).

---

## 4. Docs & config updates

- `backend/.env` — do NOT commit keys; add sample entries only if a
  `.env.example` exists (check first). Document new vars below instead:
  - Backend `.env`: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`,
    `OPENAI_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`,
    `LLM_MAX_REQUESTS_PER_MINUTE`, `LLM_MIN_REQUEST_INTERVAL_SECONDS`,
    `ANALYSIS_MIN_INTERVAL_SECONDS`, `FUNDAMENTALS_CACHE_TTL_SECONDS`
- `PLAN.md` — add "Status" section: implemented (Phase 1; AI analysis slice as
  described here) vs deferred (vision-plan items: news pipeline §17–21,
  transactions §6, price history persistence, correlations §29, portfolio
  drawdown tracking §30, capital allocation §51, thesis tracking §37, extended
  alerts §57, recommendation change detection §56, eval harness §78–80,
  multi-source reconciliation §92, corporate actions §22, peer comparison §15
  beyond yfinance peers).
- `AGENTS.md` — add one-line note about the analyzer + new env vars + that
  `LLM_PROVIDER=mock` is the offline default.
- `requirements.txt` — no new dependencies expected (httpx already present;
  yfinance present). Confirm no openai/google SDK added.

---

## 5. Build Order (implementation sequence)

1. Backend config + models + schemas (AnalysisRun, Recommendation, InvestmentProfile)
2. LLM layer (base, json extraction, openai, gemini, mock, registry)
3. Market data provider (yfinance OHLCV)
4. Fundamentals provider (yfinance snapshot + TTL cache)
5. Technical indicators
6. Evidence builder + data quality / gates
7. Prompt files v1 (4 files)
8. Orchestrator + run guards
9. Analysis router + profile router, wire into main.py
10. Backend tests (indicators, evidence, json, mock provider, API e2e w/ mock);
    run `cd backend && .venv\Scripts\python.exe -m pytest tests -q`
11. Frontend types + api client + polling helper
12. Stock detail page
13. Portfolio AI page + holdings table AI column + nav
14. `cd frontend && npm.cmd run lint` then `npm.cmd run build`
15. Docs: PLAN.md status, AGENTS.md note
16. Manual check: backend boots with LLM_PROVIDER=mock; UI renders desktop+mobile

### Implementation conventions (repo rules)

- No code comments unless requested (AGENTS.md). Docstrings: keep minimal/none
  to match repo style; check existing files (they have none — follow that).
- Backend: Pydantic v2 style, type hints everywhere, follow `schemas.py`
  alias/camelCase conventions, user-scoped queries, `Numeric` columns for money.
- Frontend: TypeScript, no new deps, mirror `lib/api.ts` patterns.
- PowerShell: never `&&`; use `; if ($?) { ... }`; never `cd`, use workdir param.

---

## 6. Status Tracker

Legend: ⬜ not started · 🟡 in progress · ✅ done · ⏸ deferred (documented, do not build now)

| # | Item | Status |
|---|------|--------|
| 0 | This plan document written | ✅ |
| 1 | Config + DB models (AnalysisRun, Recommendation, InvestmentProfile) | ✅ |
| 2 | Schemas for analysis/profile | ✅ |
| 3 | LLM layer: base + JSON extraction + OpenAI + Gemini + Mock + registry | ✅ |
| 4 | Market data provider (yfinance OHLCV) | ✅ |
| 5 | Fundamentals provider (yfinance snapshot + cache) | ✅ |
| 6 | Technical indicators + snapshot builder | ✅ |
| 7 | Evidence pack + data quality/gates | ✅ |
| 8 | Prompt files v1 (fundamental, technical, portfolio, committee) | ✅ |
| 9 | Orchestrator (holding + portfolio runs) | ✅ |
| 10 | Analysis + profile routers, main.py wiring | ✅ |
| 11 | Backend tests + pytest green | ✅ |
| 12 | Frontend types + api client + poll helper | ✅ |
| 13 | Stock detail page (analyze flow + recommendation view) | ✅ |
| 14 | Portfolio AI page + holdings table AI column + nav | ✅ |
| 15 | Frontend lint + build green | ✅ |
| 16 | Docs: PLAN.md status section, AGENTS.md note | ✅ |
| 17 | Manual smoke check (mock provider end-to-end) | 🟡 |

Deferred (out of scope this iteration — recorded in PLAN.md):
news pipeline, transactions table, price-history persistence, correlation &
drawdown analytics, capital allocation engine, structured thesis tracking,
recommendation change detection UI, LLM eval harness, multi-source
reconciliation, corporate actions tracking, sector/peer deep data.

⏸ — do not implement these until explicitly re-scoped.

---

## 7. Environment Variables Reference

Backend (`.env`):
```
LLM_PROVIDER=mock                     # mock | openai | gemini
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1   # any OpenAI-compatible endpoint
OPENAI_MODEL=gpt-4o-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
LLM_MAX_REQUESTS_PER_MINUTE=15
LLM_MIN_REQUEST_INTERVAL_SECONDS=0
ANALYSIS_MIN_INTERVAL_SECONDS=300
FUNDAMENTALS_CACHE_TTL_SECONDS=21600
```

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| yfinance rate limits / flakiness during analysis | Sequential per-symbol fetch, TTL cache, partial-completion semantics, clear error on run row |
| LLM returns non-JSON | Two retries, fence stripping, substring extraction, structured error on run |
| Background task DB session misuse | New sessionmaker() session per stage; commit between stage updates |
| Stale LTP in evidence | Evidence freshness flags; prompt instructed to penalize stale data (§40.6); UI shows timestamps (§54) |
| Render free-tier cold starts killing long runs | Per-stage commits preserve progress; run stays RUNNING only while process alive; next attempt allowed after failure |
| Prompt injection / over-trusting user notes | User fields (broker/sector/symbol) passed as data values, never as instructions; profile has no free-text fields this iteration |
| Cost | MockProvider default; real providers only when configured + interval guard |
