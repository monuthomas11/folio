# Tradebook FnO Expansion Plan

## Summary

Extend the existing `/tradebook` into two persistent views:

- **Equity** — preserve the current long/short equity ledger.
- **F&O** — add index and stock futures plus long index/stock Call and Put trades.

The first F&O release will support single-leg trades with one entry and multiple partial exits. F&O short trades will not be exposed initially, but the data model and calculation service will remain direction-aware for future support.

NSE contract metadata should be stored as a snapshot because instrument type, underlying, expiry, option type, strike, tick size, and lot sizes are exchange-controlled and can change over time. See the [NSE equity-derivatives contract specifications](https://www.nseindia.com/static/products-services/equity-derivatives-contract-specifications).

## Data and calculation changes

Extend the existing `trades` and `trade_exits` ledger with an `asset_class` discriminator instead of creating duplicate equity/F&O implementations.

F&O trade fields:

| Group | Required details |
|---|---|
| Contract | Exchange, index/stock classification, underlying symbol, futures/options type, contract symbol, expiry date, strike price for options, CE/PE for options, lot size |
| Position | Long direction, number of lots, derived units, product type such as NRML/MIS, optional margin used |
| Entry | Entry date/time, average entry price or premium, broker, broker order ID, contract-note reference |
| Exit | Exit date/time, lots exited, derived units, exit price/premium, exit reason, broker order ID, contract-note reference, notes |
| Journal | Setup/strategy tag, thesis, free-form notes |
| Pricing | Current contract mark, mark source, mark timestamp |

F&O validation rules:

- Futures require expiry and lot size but reject strike and option type.
- Options require expiry, strike, option type, and lot size.
- Option type is restricted to `CE` or `PE`.
- Lots and partial exits must be whole numbers.
- Exit lots cannot exceed remaining lots.
- Expiry cannot precede entry.
- Existing equity trades remain valid and are classified as equity during migration.

Add a `trade_charges` record for each entry and exit fill with:

- Brokerage
- STT/CTT
- Exchange transaction charges
- SEBI charges
- GST
- Stamp duty
- IPFT
- Other charges
- Contract-note reference
- Charge completeness status

Rates must not be hard-coded to one broker. Actual contract-note values are the source of truth because charges vary by broker, exchange, product, and order context. These categories correspond to the charge components shown in [Zerodha’s current charge breakdown](https://zerodha.com/charges) and its [contract-note guidance](https://support.zerodha.com/category/console/reports/contract-note/articles/virtual-contract-note).

All backend calculations should use `Decimal` and database `Numeric` values:

- F&O units: `lots × lot_size`
- Futures gross P/L: `(exit price − entry price) × units`
- Long option gross P/L: `(exit premium − entry premium) × units`
- Partial-exit P/L: calculate independently for each exit lot.
- Entry charges are allocated proportionally between exited and remaining units.
- Net realized P/L = gross realized P/L − allocated entry charges − exit charges.
- Net unrealized P/L = gross unrealized P/L − charges allocated to remaining units.
- Net total P/L is returned as unknown when required charge data or the current mark is missing.
- No intermediate currency rounding; quantize only at the final INR display/API boundary using a defined currency rounding policy.
- Strike price is stored for contract identity but does not replace premium-based P/L calculation.
- Expiry outcomes are recorded through an explicit exit/settlement price; no automatic expiry assumption is made.

Existing equity API fields remain backward-compatible. New responses add explicit gross/net values, charge totals, charge completeness, exposure, lots, units, and contract metadata.

## API and frontend interfaces

Add an optional `assetClass` filter:

- `GET /tradebook?assetClass=equity|fno`
- Default remains `equity` for compatibility.
- Each tab receives its own trades and summary; no mixed equity/F&O totals.

Extend existing mutation contracts:

- `POST /tradebook`
- `PUT /tradebook/{id}`
- `DELETE /tradebook/{id}`
- `POST /tradebook/{id}/exits`

Add:

- `PUT /tradebook/{id}/mark` — manually record a futures price or option premium.
- `POST /tradebook/fetch-all?assetClass=fno` — on-demand exchange quote refresh with per-contract error reporting.
- `PUT /tradebook/{id}/charges` — correct entry charges after receiving the contract note.
- `PUT /tradebook/{id}/exits/{exitId}/charges` — correct exit charges independently.

FnO quote refresh will use an exchange-compatible contract quote provider when the contract symbol can be resolved. Manual marks remain available whenever the provider is unavailable or cannot identify the contract. The underlying index/stock price must never be used as an option premium.

The Tradebook page will add persistent tabs, preferably `/tradebook?tab=equity` and `/tradebook?tab=fno`, with:

- Separate KPI summaries for each tab.
- F&O KPIs for gross/net realized P/L, gross/net unrealized P/L, charges, total P/L, open exposure, open/closed count, win rate, and incomplete-price/charge counts.
- Filters for instrument type, underlying, open/closed status, expiry, broker, and date range.
- F&O table/card fields for contract identity, expiry, strike, CE/PE, lots, units, entry price, mark, exit history, gross P/L, charges, net P/L, and status.
- A dynamic F&O form with conditional fields for futures versus options.
- Exit dialog with lot quantity, exit premium/price, exit reason, actual charges, and gross/net preview.
- Clear “charges incomplete” and “mark unavailable” states instead of displaying misleading net zero values.
- Expiry warnings for open contracts, without automatically closing or settling them.
- Responsive desktop table and mobile cards, keyboard-accessible dialogs, visible focus states, tabular numerals, and non-color-only gain/loss indicators.

## Migration, compatibility, and boundaries

- Additive migration only; existing equity trades and exits must remain unchanged.
- Existing equity short trades continue to work.
- New F&O records accept long direction only.
- Keep `side` and formulas generic enough to support short futures/options later.
- Do not automatically create, modify, or close Portfolio holdings.
- Do not mix F&O P/L into the Portfolio dashboard.
- Do not add multi-leg spreads, straddles, strangles, rolling, broker import, daily MTM history, or automatic expiry processing in this release.
- Do not store price-history snapshots; only the current contract mark is retained.
- Index and stock F&O are limited to Indian equity derivatives in INR.

## Test and acceptance plan

Backend tests must cover:

- Existing equity trade compatibility after migration.
- Index futures, stock futures, index options, and stock options.
- CE and PE trades using identical premium-based formulas.
- Lot-size/unit derivation and whole-lot validation.
- Partial exits and final closure.
- Entry and exit charge aggregation.
- Proportional allocation of entry charges after partial exits.
- Missing marks and incomplete charges producing pending net values.
- Decimal precision, currency rounding, large notionals, and zero/near-zero P/L.
- Invalid contract combinations and expired-contract handling.
- Manual mark updates and exchange-refresh fallback.
- User isolation and `assetClass` filtering.
- Separate equity and F&O summaries.
- Attempted F&O short creation returning a clear validation error.
- Existing equity long/short behavior remaining unchanged.

Frontend verification must cover:

- Equity/F&O tab persistence and independent loading/error/empty states.
- Conditional futures/options form fields.
- Charge entry and correction flows.
- Gross versus net P/L display.
- Missing mark and incomplete-charge warnings.
- Partial-exit preview and remaining-lot validation.
- Expiry warning state.
- Desktop and approximately 390px mobile layouts.
- Keyboard navigation, dialog focus, escape behavior, screen-reader labels, and reduced motion.

Run the backend suite, frontend lint, frontend production build, and the Impeccable detector once against the changed UI targets after implementation.

## Assumptions and defaults

- “Long FnO” includes long futures, long Calls, and long Puts.
- F&O prices are per-unit futures prices or option premiums; lot size converts them into contract value.
- Actual charges may be entered later; until then, gross P/L remains available but net P/L is explicitly marked provisional.
- A physical settlement or exercise does not automatically create an equity Portfolio holding; it is recorded as a manually entered settlement/exit event.
- Short F&O support is intentionally deferred from the UI despite the shared direction-aware model.
