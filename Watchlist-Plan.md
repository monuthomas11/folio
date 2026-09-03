# Folio Watchlist Implementation Plan

## Status

- Planning: complete
- Implementation: complete
- Last updated: 2026-09-03
- Product decisions: confirmed below

## Implementation Status

All planned watchlist MVP work is implemented and verified.

- Backend models, schemas, CRUD, manual refresh, level evaluation, and combined alerts are complete.
- Frontend navigation, responsive watchlist page, repeatable level form, alert states, and portfolio prefill are complete.
- Backend coverage is in `backend/tests/test_watchlist.py`; test cleanup includes the new tables.
- Verification on 2026-09-03: backend `92 passed`; frontend lint passed; frontend production build passed; Impeccable detector returned no findings for changed UI targets.
- No known continuation work remains for this plan. If a later session resumes it, start with the verification commands below and review the implementation notes before making changes.

### Implementation Notes

- New tables are additive and are created by the existing startup metadata/migration flow: `watchlist_items`, `watchlist_levels`, and `watchlist_alerts`.
- Holding alerts remain in `alerts`; `/alerts` and `/dashboard` merge holding and watchlist alert rows while preserving nullable source IDs in the response contract.
- `WatchlistLevel.condition_met` provides false-to-true alert transitions. Dismissing an alert does not re-alert until a later refresh observes the condition as false and then true.
- Watchlist refresh uses the existing yfinance service and remains manual. Batch refresh keeps partial-success behavior.
- The portfolio prefill flow only carries the symbol and unambiguous single point stop-loss/target levels; quantity and average buy price remain required.
- The secure external write integration is implemented: `POST /api/v1/watchlist` uses one-time-disclosed, revocable per-user API keys, strict bounded JSON validation, security headers, and rate limiting.
- External integration coverage is in `backend/tests/test_external_watchlist_api.py`, including missing/invalid/revoked keys, key hashing, unknown/unsafe/oversized payloads, user scoping, and rate limits.
- The maintainable integration reference is [Watchlist-API.md](Watchlist-API.md); update it alongside any future endpoint or schema change.

## Goal

Add a separate Watchlist feature for tracking stocks before purchase, with user-defined entry zones, targets, stop-losses, invalidation zones, notes, current LTP, and manual in-app alerts.

The watchlist remains separate from portfolio holdings. Each user may have one watchlist item per symbol, with any number of flexible level rows.

## Confirmed Product Decisions

- Use flexible level rows rather than fixed fields.
- One watchlist item per symbol per user.
- Each level has a type, optional label, lower price, and optional upper price.
- A missing upper price represents a point level; both prices represent a zone.
- Supported level types: `entry`, `target`, `stop-loss`, and `invalidation`.
- Refresh prices manually and create dismissible in-app alerts.
- Keep watchlist refresh separate from portfolio refresh endpoints.
- Provide an explicit “Add to portfolio” action that prefills the existing holding form.
- Re-alert only after the price leaves the trigger condition and later re-enters it.

## Data Model

Add three SQLAlchemy models in `backend/app/models.py`.

### WatchlistItem

- `id`: UUID primary key
- `user_id`: UUID foreign key to `users.id`, indexed
- `symbol`: uppercase exchange symbol, maximum 20 characters
- `notes`: optional text for thesis or context
- `current_ltp`: nullable numeric price
- `last_updated`: nullable timestamp
- `created_at`: timestamp
- `updated_at`: timestamp if consistent with existing model conventions
- Unique constraint on `(user_id, symbol)`

### WatchlistLevel

- `id`: UUID primary key
- `watchlist_item_id`: UUID foreign key, indexed, cascade on item deletion
- `kind`: one of `entry`, `target`, `stop-loss`, `invalidation`
- `label`: optional short label such as “Breakout entry” or “Final target”
- `lower_price`: required positive numeric price
- `upper_price`: optional positive numeric price, always greater than or equal to `lower_price`
- `sort_order`: integer for stable user-defined display order
- `condition_met`: boolean used to prevent repeated alerts while a condition remains true
- `created_at`: timestamp
- `updated_at`: timestamp if supported by the existing conventions

### WatchlistAlert

- `id`: UUID primary key
- `user_id`: UUID foreign key to `users.id`, indexed
- `watchlist_item_id`: UUID foreign key, indexed
- `watchlist_level_id`: UUID foreign key, indexed
- `symbol`: stored symbol for display consistency with existing alerts
- `kind`: `entry-reached`, `target-reached`, `stop-loss-hit`, or `invalidation-hit`
- `price`: observed LTP that triggered the alert
- `message`: generated readable message
- `dismissed`: boolean, default false
- `created_at`: timestamp

Keep the existing holding `Alert` table intact. Use a combined alert response layer so existing holding alerts remain backward compatible without requiring a risky alteration of the current table.

## Backend API

Add a protected router at `/watchlist`.

### Watchlist CRUD

- `GET /watchlist`
  - Return the authenticated user’s items ordered by creation time descending.
  - Include nested levels ordered by `sort_order`.
- `POST /watchlist`
  - Accept symbol, optional notes, and an initial list of levels.
  - Normalize the symbol to uppercase.
  - Return `409` for a duplicate symbol owned by the same user.
- `PUT /watchlist/{id}`
  - Require ownership.
  - Update item fields and replace the complete level list transactionally.
  - Preserve stable level order from the submitted list.
- `DELETE /watchlist/{id}`
  - Require ownership.
  - Cascade-delete levels and watchlist alerts.
  - Return `204`.

### Manual Price Refresh

- `POST /watchlist/fetch-price/{symbol}`
  - Require that the symbol exists in the authenticated user’s watchlist.
  - Fetch the LTP through the existing yfinance path.
  - Update all matching watchlist state for that symbol and evaluate its levels.
  - Return symbol, LTP, and `last_updated`.
- `POST /watchlist/fetch-all`
  - Fetch each distinct watched symbol once.
  - Update successful items and evaluate their levels.
  - Return the updated watchlist items; retain existing behavior for per-symbol fetch failures.

### Combined Alerts

Extend the existing alert response contract so an alert can identify either:

- A holding through `holdingId`.
- A watchlist item and level through `watchlistItemId` and `watchlistLevelId`.

Make holding-specific identifiers nullable for watchlist alerts. Extend:

- `GET /alerts`
- `GET /alerts?include_dismissed=true`
- `PUT /alerts/{id}/dismiss`
- `GET /dashboard`

The combined endpoints must merge both alert sources, sort by creation time descending, enforce `user_id` ownership, and include active watchlist alerts in the dashboard’s active alert count.

## Alert Semantics

Evaluate levels only after an explicit watchlist price refresh. Do not add a scheduler, background price refresh, or price-history table.

- Entry zone: triggered when LTP is inside the inclusive range.
- Point entry: triggered when LTP is at or below the point.
- Target zone: triggered when LTP enters the inclusive range.
- Point target: triggered when LTP is at or above the point.
- Stop-loss zone: triggered when LTP enters the inclusive range.
- Point stop-loss: triggered when LTP is at or below the point.
- Invalidation zone: triggered when LTP enters the inclusive range.
- Point invalidation: triggered when LTP is at or below the point.

On refresh:

1. Calculate the current condition for each level.
2. Create an alert only on a false-to-true transition.
3. Set `condition_met` to the current condition.
4. Do not create another alert merely because an existing alert was dismissed while the condition remains true.
5. Re-arm the level only after a refresh reports the condition as false.

Because Folio remains current-state only, a refresh that skips over a range cannot prove that the price entered it; no historical crossing inference is required.

## Frontend

### Navigation and Types

- Add a Watchlist item to the desktop sidebar and mobile drawer.
- Add `WatchlistItem`, `WatchlistLevel`, `WatchlistInput`, and watchlist alert types in `frontend/src/lib/types.ts`.
- Add CRUD, refresh, and combined-alert methods to `frontend/src/lib/api.ts`.
- Extend alert-kind rendering to cover entry and invalidation alerts.

### `/watchlist` Page

Build a client page using the existing `AppShell`, design tokens, controls, skeletons, and responsive table patterns.

Desktop rows should show:

- Symbol
- Current LTP and last refresh
- Entry zones
- Targets
- Stop-loss and invalidation levels
- Current level/alert state
- Refresh, edit, delete, and Add to portfolio actions

On mobile, use stacked rows with level details that remain readable without horizontal scrolling.

### Add/Edit Form

Provide a repeatable level editor with:

- Symbol
- Optional thesis/notes
- Level type selector
- Optional label
- Lower price
- Optional upper price
- Add level and remove level controls

Validate required symbols, positive prices, valid ranges, and at least one level only if the product flow requires a non-empty setup. The recommended default is to allow a watchlist item without levels, while making level addition prominent.

### Add to Portfolio

Navigate to the existing portfolio holding form with prefilled values:

- Always prefill symbol.
- Prefill stop-loss only when there is exactly one point stop-loss level.
- Prefill target only when there is exactly one point target level.
- Leave ranged or ambiguous levels for explicit review.
- Always require quantity and average buy price from the user.
- Never create a holding automatically.

### Dashboard and Alerts UX

- Include watchlist alerts in the existing dashboard alert strip and active alert badge.
- Show watchlist-specific alert labels and links back to `/watchlist`.
- Preserve holding alert labels and interactions.
- Use text labels, not color alone, for triggered, risk, target, and neutral states.
- Keep focus rings, keyboard operation, responsive behavior, and reduced-motion support consistent with `DESIGN.md`.

## Persistence and Compatibility

The repository currently uses SQLAlchemy `Base.metadata.create_all` at startup and a lightweight SQLite additive migration helper. Add only new tables and relationships, so existing SQLite and PostgreSQL data remains intact and new tables are created on startup.

Update test cleanup fixtures to delete watchlist alerts and levels before users. Do not change existing holding columns or existing alert rows.

## Test Plan

Add `backend/tests/test_watchlist.py` covering:

- Create and list a watchlist item with nested levels.
- Update item notes and replace/add/remove level rows.
- Positive-price and invalid-range validation.
- Duplicate symbol rejection.
- User isolation for list, read/update, delete, and refresh operations.
- Cascade deletion of levels and watchlist alerts.
- Single-symbol and batch price refresh using mocked market data.
- Entry, target, stop-loss, and invalidation point/range semantics.
- One alert per false-to-true transition.
- Dismissal without repeated alerts while still triggered.
- Re-alert after leaving and re-entering a condition.
- Combined `/alerts` and `/dashboard` results.
- Cross-user dismissal rejection.

Run the full verification suite:

```text
backend\\.venv\\Scripts\\python.exe -m pytest tests -q
frontend\\npm.cmd run lint
frontend\\npm.cmd run build
```

After UI implementation, run the Impeccable detector once over the changed frontend targets:

```text
node C:\\Users\\monut\\.agents\\skills\\impeccable\\scripts\\detect.mjs --json <changed-targets>
```

## Scope Boundaries

Not included in this implementation:

- CSV import/export for watchlist items.
- Watchlist groups or folders.
- Broker, quantity, or buy-price fields on watchlist items.
- Automatic price polling, scheduled jobs, email, or push notifications.
- Historical prices or charting.
- Automatic synchronization between watchlist levels and holdings.
- AI analysis specifically for watchlist items.

## Resume Checklist

- [x] Add watchlist SQLAlchemy models and relationships.
- [x] Add Pydantic request/response schemas.
- [x] Add protected watchlist CRUD router.
- [x] Add manual price refresh and level evaluation service.
- [x] Merge watchlist alerts into existing alert/dashboard responses.
- [x] Add backend tests and update test fixtures.
- [x] Add frontend types and API methods.
- [x] Add Watchlist navigation and page.
- [x] Add repeatable watchlist form and responsive level display.
- [x] Add Add-to-portfolio prefill flow.
- [x] Update alert UI for watchlist alert kinds.
- [x] Run backend tests, frontend lint/build, and the Impeccable detector.
- [x] Review changed files and confirm no secrets or unrelated changes.

## External API Integration

The watchlist also exposes a server-to-server write API:

- `POST /api/v1/watchlist`
- Authentication: `X-Folio-API-Key: <key>`
- Body: the same camelCase `WatchlistIn` payload used by the app (`symbol`, optional `notes`, and optional `levels`).
- Success: `201` with the created watchlist item.
- Duplicate symbol: `409`; malformed, oversized, unsafe-symbol, or unknown fields: `422`/`413`; missing, invalid, or revoked key: `401`; rate limit: `429`.

Create and revoke keys through the authenticated endpoints `POST /auth/api-keys`, `GET /auth/api-keys`, and `DELETE /auth/api-keys/{id}`. The raw key is returned only once when created; only a SHA-256 hash and short prefix are persisted.

Example:

```bash
curl -X POST https://<folio-api-host>/api/v1/watchlist \
  -H "X-Folio-API-Key: folio_wk_<secret>" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"INFY","notes":"Imported idea","levels":[{"kind":"entry","lowerPrice":1400,"upperPrice":1450}]}'
```

Keep the API key in a server-side secret store. Do not place it in browser JavaScript, URLs, logs, or client-side source. HTTPS must be enabled at the public host; CORS is not an authentication mechanism. The endpoint uses parameterized SQL through SQLAlchemy, bounded JSON fields/levels, strict unknown-field rejection, JSON-only responses, security headers, and per-IP/per-key in-memory rate limiting.

## Product Documentation Note

The repository’s `PRODUCT.md` contains an obsolete `## Register` section reported by the Impeccable context check. Removing that unrelated section is intentionally outside this feature implementation.
