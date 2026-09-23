# Tradebook Plan

## Summary

Add a dedicated, user-scoped Tradebook separate from Portfolio holdings. It tracks manual long and short equity trades, supports partial exits, and shows per-trade and total gross realized/unrealized P/L in INR. Zerodha import is explicitly deferred.

## Key Changes

- Add `trades` and `trade_exits` records:
  - Trade: symbol, side (`long`/`short`), entry date, entry price, original quantity, broker, optional notes, LTP, and last refresh time.
  - Exit lot: parent trade, exit date, quantity, exit price.
  - Derive remaining quantity, status, realized P/L, and unrealized P/L rather than storing calculated values.
  - Keep all records isolated by `user_id`; add relationships and test-fixture cleanup.

- Add Tradebook API and frontend types:
  - `GET /tradebook` returns the user’s trades, each trade’s exit history, and Tradebook totals.
  - `POST /tradebook`, `PUT /tradebook/{id}`, and `DELETE /tradebook/{id}` create, correct, or remove trades only before the first exit.
  - `POST /tradebook/{id}/exits` records an exit lot; validate positive quantity, remaining quantity, and an exit date not before entry.
  - `POST /tradebook/fetch-all` refreshes LTP for open trades.
  - Extend the existing holdings batch refresh to also refresh matching open Tradebook trades, so Dashboard’s existing **Refresh prices** updates all open positions without changing entry or exit records.

- Use gross P/L formulas:
  - Long realized: `(exit price - entry price) x exited quantity`; unrealized: `(LTP - entry price) x remaining quantity`.
  - Short realized: `(entry price - cover price) x exited quantity`; unrealized: `(entry price - LTP) x remaining quantity`.
  - Tradebook totals show realized P/L, unrealized P/L for priced open trades, and combined P/L. Trades without an LTP show a pending value rather than a misleading zero.

- Add a `/tradebook` navigation entry and an operating-focused ledger UI:
  - Header with **Add trade** and secondary **Refresh prices** actions.
  - Manual form for side, symbol, entry date, quantity, entry price, broker, and optional notes.
  - Desktop table and mobile cards showing side, entry details, remaining/open status, LTP, realized P/L, unrealized P/L, and total P/L.
  - Expandable exit history below each trade; partial exits retain one parent trade row with cumulative realized P/L.
  - Exit dialog supports a quantity, price, and exit date; it previews the realized P/L before saving.
  - Once any exit exists, lock edits and deletion for the whole trade, while allowing further exits until quantity reaches zero.
  - Keep the current Portfolio holding-exit history and Dashboard’s existing portfolio realized-P/L metric unchanged, avoiding mixed totals between two independent ledgers.

## Test Plan

- Backend coverage for long and short formulas, full/partial exits, total aggregation, date/quantity validation, immutable-after-first-exit behavior, user isolation, and refresh behavior with missing prices.
- API tests for create/list/update/delete/exit flows and returned calculated fields.
- Frontend checks for empty, loading, error, pending-price, open, partially exited, and closed states; verify keyboard-accessible dialogs and responsive table-to-card behavior.
- Run the backend suite and frontend lint/build after implementation.

## Assumptions

- V1 supports equities only, including long and short trades; futures, options, leverage, taxes, brokerage charges, and net P/L are out of scope.
- Tradebook entries never create, merge, reduce, or delete Portfolio holdings.
- Zerodha trade-history import is a future enhancement; no upload control or parser is included now.
