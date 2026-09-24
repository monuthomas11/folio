# AGENTS.md

Guidance for AI coding agents working in this repository. Read PRODUCT.md (product truth) and PLAN.md (phased roadmap) alongside this file.

## Project Overview

**Folio** — a multi-user web app for tracking personal share holdings in Indian markets (NSE/BSE, INR). Users record positions (symbol, quantity, average buy price, stop-loss, target, broker), fetch the last traded price on demand from yfinance, and view a consolidated dashboard with P/L and in-app alerts.

**Status:** Phase 1 MVP implemented — FastAPI backend (`backend/`) with auth, holdings CRUD, yfinance LTP fetch, and alerts; Next.js frontend (`frontend/`) wired to it with login/register and dashboard/portfolio/alerts pages. See PLAN.md for remaining phases. AI Portfolio Analyzer (on-demand analysis via Mock/OpenAI/Gemini providers) also implemented — see Analyzer-Implementation-Plan.md.

## Architecture & Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Frontend | Next.js 14 (React, TypeScript, App Router) | `frontend/` |
| Backend | FastAPI (Python) | `backend/` |
| Market data | yfinance | NSE symbols use `.NS` suffix (e.g. `RELIANCE.NS`) |
| Local DB | SQLite | dev only |
| Production DB | Neon.tech PostgreSQL | prod only |
| Hosting | Render (free tier) | cold starts + resource limits apply |
| Auth | JWT + bcrypt | email/password, per-user data isolation |

Two-app layout (frontend + backend), see PLAN.md §1.1.

## Core Product Rules (do not violate)

1. **User record is the source of truth.** Quantity, buy price, SL, target, broker come from the user. yfinance supplies ONLY the LTP. Never auto-overwrite user-entered prices.
2. **Manual/on-demand LTP fetch only.** No background scheduler, no automated daily cron.
3. **Current-state only.** No historical price snapshots, no price history storage in the MVP.
4. **In-app alerts only.** Alerts surface in the dashboard (SL/target hits); no email/push. Alerts can be dismissed.
5. **Multi-user privacy.** Every query must be scoped by `user_id`; users see only their own holdings and alerts.
6. **India market conventions.** Currency INR, symbols stored with exchange suffix for yfinance.

## Data Model (MVP)

- **users:** id (UUID PK), email (unique), password_hash, name, created_at
- **holdings:** id (UUID PK), user_id (FK), symbol, quantity, avg_buy_price, stop_loss (nullable), target_price (nullable), broker (nullable), current_ltp (nullable), last_updated (nullable), created_at
- **alerts** (Phase 1): per holding, triggered when LTP crosses SL or target, dismissible

## Key API Surface (planned)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /auth/register | Register |
| POST | /auth/login | Login → JWT |
| GET | /holdings | List (user-scoped) |
| POST | /holdings | Add holding |
| PUT | /holdings/{id} | Update |
| DELETE | /holdings/{id} | Delete |
| POST | /holdings/fetch-price/{symbol} | Fetch LTP (single) |
| POST | /holdings/fetch-all | Batch refresh |
| GET | /alerts | User alerts |
| PUT | /alerts/{id}/dismiss | Dismiss alert |

## Running the App

From the repo root (`E:\Repos\folio`), run each in its own terminal. Note the `.\` prefix — PowerShell does not resolve scripts in the current directory otherwise:

```
.\run-backend.cmd     # FastAPI at http://localhost:8000  (auto-reload)
.\run-frontend.cmd    # Next.js at http://localhost:3000
```

Both scripts `cd` into their own folder and invoke the venv/npm, so you don't need to navigate. Manual equivalents:

- Backend: `cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm.cmd run dev`

Open `http://localhost:3000`, register an account, add a holding, then use **Refresh prices** / per-row **Fetch** to pull live LTP via yfinance. The frontend reads `NEXT_PUBLIC_API_URL` from `frontend/.env.local` (default `http://localhost:8000`).

## Environment Variables

Backend `.env`: `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM=HS256`, `ACCESS_TOKEN_EXPIRE_MINUTES`
Frontend `.env.local`: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_HEARTBEAT_TIMEOUT_MINUTES=60`

`NEXT_PUBLIC_HEARTBEAT_TIMEOUT_MINUTES` controls how long the authenticated browser heartbeat
continues after the last activity. Invalid or non-positive values fall back to 60 minutes.
Because this is a public Next.js environment variable, changes require a frontend rebuild/redeploy.

AI analyzer env vars (backend `.env`, see `Analyzer-Implementation-Plan.md`): `LLM_PROVIDER=mock` is the
offline default (no key needed); `OPENAI_API_KEY`/`OPENAI_BASE_URL`/`OPENAI_MODEL`,
`GEMINI_API_KEY`/`GEMINI_MODEL`, `LLM_MAX_REQUESTS_PER_MINUTE=15`,
`LLM_MIN_REQUEST_INTERVAL_SECONDS=0`, `ANALYSIS_MIN_INTERVAL_SECONDS=300`,
`FUNDAMENTALS_CACHE_TTL_SECONDS=21600`.

Use SQLite locally (`sqlite:///./folio.db`), Neon Postgres in production. Never commit secrets.

## Roadmap (from PLAN.md)

- **Phase 1 — MVP:** auth, holdings CRUD, manual LTP fetch, dashboard, in-app alerts
- **Phase 2:** charts (allocation, gainers/losers), alerts history, bulk CSV add
- **Phase 3:** price history storage + technical indicators (SMA/RSI/MACD/Bollinger), candlestick charts
- **Phase 4:** fundamentals + AI-assisted explanations

Build and verify phases in order. Do not implement Phase 3–4 features during Phase 1–2 work.

## Conventions

- **No code comments** unless explicitly requested.
- TypeScript on the frontend, type hints on the backend (Pydantic schemas).
- Follow the directory layout in PLAN.md §1.1 when scaffolding.
- Preserve user-entered values exactly; format currency/percent for display only (INR).
- After making UI changes, verify responsive behavior on desktop and mobile widths.

## Verification

- Backend tests: `cd backend && .venv\Scripts\python.exe -m pytest tests -q`
- Frontend build: `cd frontend && npm.cmd run build`
- Frontend lint: `cd frontend && npm.cmd run lint`
