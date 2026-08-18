# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

User-decided stack:
- Frontend: Next.js (React, TypeScript)
- Backend: FastAPI (Python)
- Market data: yfinance
- Local DB: SQLite
- Production DB: Neon.tech PostgreSQL
- Hosting: Render (free tier)

## Users

Primary user is the owner — a retail investor in Indian markets (NSE/BSE) tracking personal share holdings. Secondary (optional, later): friends/family who can each track their own portfolio; auth exists to enable this sharing.

## Product Purpose

A personal share-holdings tracker: the user records what they own (symbol, quantity, buy price, planned stop-loss and target, broker), fetches the latest price on demand, and sees a consolidated dashboard of portfolio value, performance, and in-app alerts. Success means the user can tell at a glance whether each position is healthy, at its stop-loss, or at its target.

## Positioning

A focused, current-state holding tracker built around Indian retail conventions (NSE/BSE symbols, INR). The user's manual record — quantity, buy price, stop-loss, target, broker — is the source of truth; yfinance supplies only the last traded price. It is deliberately simpler than a full broker/folio app: no automated scheduling, no push notifications, no historical bloat.

## Operating Context

- Used as a web app in a desktop browser; should remain usable on a phone browser.
- Price refresh is manual/on-demand, typically run after market hours.
- Indian market conventions: NSE symbols use the `.NS` yfinance suffix (e.g. `RELIANCE.NS`), currency is INR.
- Holdings are spread across multiple brokers; broker is captured per holding.
- Hosted on Render free tier: resource limits and cold starts apply.

## Capabilities and Constraints

Confirmed capabilities:
- Multi-user with email/password authentication (JWT, bcrypt); each user sees only their own data.
- CRUD holdings: symbol, quantity, average buy price, stop-loss, target price, broker.
- Manual LTP fetch from yfinance — single symbol and batch refresh.
- Dashboard with consolidated data: total portfolio value, total investment, P/L (absolute and %), holdings count.
- In-app alerts when an LTP crosses a stop-loss or target; alerts can be dismissed. No email.
- Current-state only: no historical price snapshots stored.

Constraints:
- No automated/daily price scheduler in scope — on-demand fetch only.
- No email or push notifications.
- No historical price storage in the MVP.
- India (NSE/BSE) market focus for now.

Deferred future work (confirmed as later, not dropped):
- Technical analysis: price history storage, SMA/RSI/MACD/Bollinger Bands, candlestick charts.
- Fundamental analysis: company financials and ratios from yfinance.
- AI-assisted explanations of stock performance and outlook.

## Brand Commitments

None established beyond the working name "Folio" used in PLAN.md. No logo, palette, typography, voice, or identity constraints are binding yet.

## Evidence on Hand

- PLAN.md: schema sketch (users, holdings), API endpoint list, phased roadmap, deployment checklist.
- No implementation code, no real user data, no screenshots, no testimonials. Future work must not fabricate user content.

## Product Principles

1. **User record is the source of truth** — positions (quantity, buy price, SL, target, broker) come from the user; external data only provides LTP.
2. **Current-state simplicity** — store only what the dashboard needs today; no historical bloat in the MVP.
3. **Manual and predictable** — price refresh is user-triggered, not silently automated.
4. **In-app signal over push** — alerts live in the dashboard the user already checks.
5. **Multi-user privacy** — holdings and alerts are isolated per user; sharing is optional and deferred.
