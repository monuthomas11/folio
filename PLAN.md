# Folio - Portfolio Tracker

## Overview
A multi-user web application to track share holdings with manual price updates, SL/target alerts, and portfolio performance analysis.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js 14 (App Router, TypeScript) |
| Backend | Python FastAPI |
| Local DB | SQLite |
| Production DB | Neon PostgreSQL |
| Hosting | Render (Free Tier) |
| Data Fetch | yfinance |
| Auth | JWT (fastapi-jwt) + bcrypt |

---

## Database Schema

### Users
```
id          UUID (PK)
email       VARCHAR(255) UNIQUE
password_hash VARCHAR(255)
name        VARCHAR(100)
created_at  TIMESTAMP
```

### Holdings
```
id              UUID (PK)
user_id         UUID (FK → users)
symbol          VARCHAR(20)       -- e.g., "RELIANCE"
quantity        DECIMAL(10,3)
avg_buy_price   DECIMAL(12,4)
stop_loss       DECIMAL(12,4) NULL
target_price    DECIMAL(12,4) NULL
broker          VARCHAR(100) NULL
current_ltp     DECIMAL(12,4) NULL
last_updated    TIMESTAMP NULL
created_at      TIMESTAMP
```

---

## Phase 1 — Foundation (MVP)

### 1.1 Project Structure
```
/folio
├── backend/           # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   └── services/
│   ├── requirements.txt
│   └── yfinance_service.py
├── frontend/          # Next.js
│   ├── app/
│   │   ├── page.tsx
│   │   ├── login/
│   │   ├── register/
│   │   ├── dashboard/
│   │   └── portfolio/
│   ├── components/
│   └── package.json
└── SPEC.md
```

### 1.2 Backend — Auth
- [ ] Register endpoint (`POST /auth/register`)
- [ ] Login endpoint (`POST /auth/login`)
- [ ] JWT token generation & refresh
- [ ] Password hashing with bcrypt
- [ ] Protected route middleware

### 1.3 Backend — Holdings CRUD
- [ ] `GET /holdings` — list user's holdings
- [ ] `POST /holdings` — add a stock
- [ ] `PUT /holdings/{id}` — update a holding
- [ ] `DELETE /holdings/{id}` — remove a holding

### 1.4 Backend — Price Fetch
- [ ] `POST /holdings/fetch-price/{symbol}` — fetch LTP from yfinance
- [ ] `POST /holdings/fetch-all-prices` — batch fetch for all holdings
- [ ] Response: symbol, ltp, last_updated

### 1.5 Backend — Alerts
- [ ] Alert model (per holding, triggered when LTP crosses SL or Target)
- [ ] `GET /alerts` — get active alerts for user
- [ ] `PUT /alerts/{id}/dismiss` — mark alert as seen

### 1.6 Frontend — Auth Pages
- [ ] Register page
- [ ] Login page
- [ ] Session persistence (localStorage JWT)

### 1.7 Frontend — Portfolio Page
- [ ] Holdings table (symbol, qty, avg price, SL, target, broker, LTP, P/L)
- [ ] Add Holding modal/form
- [ ] Edit/Delete actions per row
- [ ] Fetch Price button (single & batch)
- [ ] Inline alert indicators (red/green badges)

### 1.8 Frontend — Dashboard
- [ ] Total Portfolio Value
- [ ] Total P/L (absolute + percentage)
- [ ] Holdings count
- [ ] Active alerts count
- [ ] Quick alert summary

### 1.9 Deployment
- [ ] Render: FastAPI service (Python)
- [ ] Render: Next.js static/SSR hosting
- [ ] Neon PostgreSQL connection string in env
- [ ] Local SQLite for dev without Neon

---

## Phase 2 — Performance & Analysis

### 2.1 Enhanced Dashboard
- [ ] Sector-wise allocation pie chart (static grouping)
- [ ] Top gainers / Top losers widgets
- [ ] Portfolio P/L by stock (bar chart)

### 2.2 Alerts Dashboard
- [ ] Full alerts page with history
- [ ] Filter: active/dismissed/all
- [ ] Trigger reason display (hit SL / hit Target)

### 2.3 Bulk Operations
- [ ] Bulk add via CSV paste
- [ ] Bulk fetch prices with progress indicator

### 2.4 Portfolio Summary
- [ ] Average portfolio return %
- [ ] Total investment vs current value
- [ ] Exposed positions (stocks below SL)

---

## Phase 3 — Technical Analysis (Future)

### 3.1 Price History Storage
- [ ] Daily price snapshots table (symbol, date, open, high, low, close, volume)
- [ ] Background job to store daily OHLCV after market hours
- [ ] 30/60/90 day data retention policies

### 3.2 Technical Indicators
- [ ] SMA (20, 50, 200 day)
- [ ] RSI
- [ ] MACD
- [ ] Bollinger Bands
- [ ] Price chart with indicator overlays

### 3.3 Chart Component
- [ ] Candlestick chart (recharts or lightweight-charts)
- [ ] Indicator toggle controls

---

## Phase 4 — Fundamental Analysis + AI (Future)

### 4.1 Fundamental Data
- [ ] Company info (yfinance: income statement, balance sheet, ratios)
- [ ] Market cap, P/E, EPS, dividend yield display

### 4.2 AI Explanations
- [ ] Stock summary endpoint (news + fundamentals synthesis)
- [ ] P/L explanation
- [ ] Technical pattern recognition description
- [ ] Integration with OpenAI-compatible API

---

## AI Portfolio Analyzer — Status

Implemented (Phase 1; on-demand AI analysis slice):

- LLM provider layer (OpenAI-compatible, Gemini, Mock), selectable via `LLM_PROVIDER`
- Market data provider (yfinance OHLCV), fundamentals provider (yfinance snapshot + TTL cache)
- Deterministic technical indicators (EMA/SMA/RSI/MACD/ATR, support/resistance, trend states)
- Evidence pack builder with freshness/confidence metadata + data-quality gates
- Multi-agent orchestration: fundamental → technical → portfolio → investment committee,
  run via FastAPI `BackgroundTasks` + polling (`GET /analysis/{run_id}`)
- New tables: `analysis_runs`, `recommendations`, `investment_profiles` (existing tables untouched)
- Stock detail page (`/holdings/[id]`) with Analyze flow + full recommendation view
- Portfolio AI page (`/ai`) with health score, positives/concerns, per-stock actions
- Holdings table: per-row View link + AI rating column; "AI Advisor" nav entry
- Verified with MockProvider end-to-end (no API keys required)

Deferred (vision-plan items, out of scope this iteration):

- News pipeline (§17–21 of the vision doc), transactions table (§6), price-history persistence
- Correlations (§29), portfolio drawdown tracking (§30), capital allocation engine (§51)
- Structured thesis tracking (§37), recommendation change detection UI (§56)
- Extended alerts (§57), LLM eval harness (§78–80), multi-source reconciliation (§92)
- Corporate actions tracking (§22), sector/peer deep data beyond yfinance peers (§15)

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Register user |
| POST | /auth/login | Login, get JWT |
| GET | /holdings | List holdings |
| POST | /holdings | Add holding |
| PUT | /holdings/{id} | Update holding |
| DELETE | /holdings/{id} | Delete holding |
| POST | /holdings/fetch-price/{symbol} | Fetch LTP for symbol |
| POST | /holdings/fetch-all | Fetch all LTP |
| GET | /alerts | Get user alerts |
| PUT | /alerts/{id}/dismiss | Dismiss alert |

---

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://user:pass@host/folio
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
```

---

## Render Deployment Checklist

1. Create FastAPI app on Render → Python environment
2. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. Create Next.js app on Render → Node environment
4. Set build command: `npm run build`
5. Set start command: `npm start`
6. Add environment variables from .env
7. Connect Neon PostgreSQL