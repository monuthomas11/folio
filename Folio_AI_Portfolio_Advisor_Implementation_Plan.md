# Folio --- AI-Powered Portfolio & Holdings Advisor

## Product, Analysis Engine, Data Architecture, AI Orchestration & Implementation Plan

**Document purpose:** This document is a detailed implementation
blueprint for building **Folio**, a portfolio intelligence application
that stores the user's stock holdings and combines portfolio context,
technical analysis, company fundamentals, valuation, market/sector
context, recent news, corporate actions, and AI reasoning to produce
actionable---but risk-aware---recommendations.

**Target stack** - Backend: Python + FastAPI - Database: SQLite for
local/single-user deployments and PostgreSQL/Neon for production -
Frontend: Next.js / React - AI: Pluggable LLM provider layer -
Market/fundamental/news data: provider abstraction layer with multiple
sources and freshness tracking

------------------------------------------------------------------------

# 1. Executive Objective

Folio should not behave like a generic chatbot that receives:

> "I own 10 shares of XYZ. Should I buy more?"

and produces an opinion.

Instead, Folio should operate as a **portfolio decision-support
engine**.

For every holding, the system should first assemble a structured
evidence pack:

1.  Position and cost basis
2.  Current market price and technical state
3.  Company fundamentals
4.  Valuation
5.  Earnings/business trajectory
6.  Sector and industry conditions
7.  Recent material news
8.  Corporate actions
9.  Management/promoter/institutional signals where available
10. Risk factors
11. Portfolio concentration and correlation
12. User-specific position size and unrealized P&L
13. Existing stop-loss / target / investment horizon
14. Market regime
15. Historical evidence and trend changes

The LLM should then reason **over the structured evidence**, rather than
independently inventing or searching for facts.

The desired output is not merely:

> BUY / HOLD / SELL

but:

> **What should I do with this position, why, under what conditions, and
> what would invalidate the thesis?**

------------------------------------------------------------------------

# 2. Core Design Philosophy

## 2.1 Separate facts from reasoning

This is one of the most important architectural decisions.

The application should distinguish:

### A. Raw facts

Examples:

-   LTP = ₹1,025
-   Average buy price = ₹900
-   Quantity = 20
-   P/E = 28.4
-   Revenue growth = 17.2%
-   Debt/equity = 0.18
-   Latest quarterly PAT growth = 24%
-   Price above 50 DMA
-   Recent result announced on 12-Aug-2026
-   Promoter holding = 54.2%

### B. Derived metrics

Examples:

-   Unrealized return = +13.9%
-   Position weight = 8.6%
-   Earnings growth acceleration = +6 percentage points
-   Valuation premium vs sector = +18%
-   Technical trend score = 74/100

### C. Evidence interpretation

Examples:

-   Earnings momentum is improving.
-   Valuation is no longer cheap.
-   Technical trend remains positive.
-   Position has become oversized relative to the portfolio.

### D. Recommendation

Examples:

-   HOLD
-   HOLD / ADD ON CORRECTION
-   BUY
-   ACCUMULATE
-   REDUCE
-   EXIT
-   WATCH

The LLM should reason from A+B+C and produce D.

------------------------------------------------------------------------

# 3. Portfolio-Level Analysis Must Come First

A major mistake would be analyzing each stock independently and then
simply adding the recommendations together.

Example:

  Stock     Individual view
  --------- -----------------
  Stock A   BUY
  Stock B   BUY
  Stock C   BUY
  Stock D   BUY

That does **not** necessarily mean the portfolio should buy all four.

The portfolio may already have:

-   excessive banking exposure
-   excessive small-cap exposure
-   excessive defence exposure
-   excessive PSU exposure
-   too much exposure to one business theme
-   too much capital concentrated in a single stock
-   several stocks whose returns are highly correlated

Therefore Folio should have two separate analytical layers:

### Layer 1 --- Security analysis

> "Is this company attractive?"

### Layer 2 --- Portfolio analysis

> "Is owning more of this company appropriate for this portfolio?"

The second layer should be allowed to override the first.

Example:

> Company quality: Strong\
> Valuation: Reasonable\
> Technical trend: Positive\
> Portfolio weight: 18%\
> Recommended action: HOLD / DO NOT ADD

------------------------------------------------------------------------

# 4. User Investment Profile

Folio should maintain a configurable investor profile.

## Required fields

``` text
investment_style
risk_tolerance
investment_horizon
primary_goal
monthly_investment_capacity
preferred_market_cap
sector_preferences
sector_restrictions
maximum_single_stock_weight
maximum_sector_weight
preferred_cash_buffer
technical_trading_enabled
fundamental_investing_enabled
```

### Suggested investment styles

-   Conservative
-   Moderate
-   Moderately Aggressive
-   Aggressive

### Suggested horizons

-   Intraday
-   Short term: days/weeks
-   Swing: weeks/months
-   Medium term: 6--24 months
-   Long term: 2--5 years
-   Very long term: 5+ years

Folio should **never give the same recommendation to every investor**.

------------------------------------------------------------------------

# 5. Holdings Data Model

Each holding should contain at least:

``` text
symbol
exchange
isin
company_name

quantity
average_buy_price
total_invested
current_price
current_value

unrealized_pnl
unrealized_pnl_percent

portfolio_weight

stop_loss
target_price

purchase_date
holding_period

investment_thesis
user_notes

preferred_horizon
manual_conviction

created_at
updated_at
```

Optional:

``` text
broker
sector
industry
market_cap_category
watchlist_status
tags
```

------------------------------------------------------------------------

# 6. Transaction-Level Data

Do not store only the final average price.

If possible, maintain individual transactions.

``` text
transactions
----------------
id
holding_id
trade_date
transaction_type
quantity
price
charges
taxes
brokerage
notes
```

Supported types:

-   BUY
-   SELL
-   BONUS
-   SPLIT
-   DIVIDEND
-   RIGHTS
-   MERGER
-   DEMERGER
-   OTHER

This enables accurate:

-   average cost
-   realized P&L
-   unrealized P&L
-   holding period
-   tax-aware analysis
-   portfolio history
-   position changes

------------------------------------------------------------------------

# 7. Portfolio Database Model

Recommended high-level tables:

``` text
users
portfolios
holdings
transactions

price_history
technical_snapshots

company_profiles
fundamental_snapshots
financial_statements

valuation_snapshots
sector_snapshots

news_articles
news_events
corporate_actions

analyst_estimates
institutional_holding_snapshots

market_snapshots

analysis_runs
analysis_evidence
recommendations
recommendation_history

user_theses
alerts
data_source_status
```

Every externally sourced value should ideally carry:

``` text
source
source_url
retrieved_at
effective_date
period
confidence
```

This is essential for auditability.

------------------------------------------------------------------------

# 8. Data Freshness Architecture

Folio should never treat all data as equally fresh.

Each data point should have:

``` text
observed_at
published_at
effective_date
data_period
source
freshness_status
```

Suggested freshness categories:

### Real-time

LTP, volume, market status.

### Intraday

5-minute / 15-minute technical data.

### Daily

Daily OHLCV and end-of-day technical indicators.

### Quarterly

Financial results.

### Annual

Annual report metrics.

### Event driven

News, announcements, corporate actions.

The AI prompt should explicitly receive freshness metadata.

Example:

> P/E: 27.4 --- updated 2 hours ago\
> Revenue growth: 18.2% --- latest quarter ended Jun-2026\
> News: published 4 hours ago

------------------------------------------------------------------------

# 9. Market Data Layer

Create a provider abstraction.

``` python
class MarketDataProvider:
    def get_quote(self, symbol): ...
    def get_ohlcv(self, symbol, timeframe): ...
    def get_volume(self, symbol): ...
```

Do not hard-code a single provider into business logic.

Possible provider categories:

-   exchange/broker APIs
-   market-data APIs
-   yfinance where appropriate
-   broker APIs
-   paid APIs later

The application should be able to replace the provider without rewriting
the analysis engine.

------------------------------------------------------------------------

# 10. Fundamental Data Layer

Create:

``` python
class FundamentalDataProvider:
    def get_company_profile(self, symbol): ...
    def get_income_statement(self, symbol): ...
    def get_balance_sheet(self, symbol): ...
    def get_cash_flow(self, symbol): ...
    def get_ratios(self, symbol): ...
    def get_shareholding(self, symbol): ...
```

The system should preferably normalize financial data into a common
schema.

------------------------------------------------------------------------

# 11. Fundamental Analysis Framework

The AI should not simply read P/E and decide whether a stock is
expensive.

Analyze at least:

## Business quality

-   Business model
-   Products/services
-   Revenue sources
-   Geographic exposure
-   Customer concentration
-   Competitive position
-   Moat
-   Cyclicality
-   Regulatory dependence
-   Commodity dependence

## Growth

-   Revenue CAGR
-   EBITDA CAGR
-   EBIT CAGR
-   PAT CAGR
-   EPS CAGR
-   Operating cash-flow growth
-   Free cash-flow growth

Evaluate:

-   1Y
-   3Y
-   5Y

where data exists.

## Profitability

-   Gross margin
-   EBITDA margin
-   EBIT margin
-   PAT margin
-   ROE
-   ROCE
-   ROIC

Look for:

-   improving margins
-   declining margins
-   cyclical margins
-   abnormal one-off effects

## Balance sheet

-   Debt/equity
-   Net debt
-   Interest coverage
-   Current ratio
-   Debt trend
-   Cash position
-   Working capital
-   Contingent liabilities where available

## Cash flow

This should receive substantial weight.

Compare:

``` text
PAT
Operating Cash Flow
Free Cash Flow
```

Flag:

> PAT growing rapidly while operating cash flow remains weak.

Also analyze:

-   CFO/PAT
-   FCF consistency
-   capex intensity
-   working capital absorption

------------------------------------------------------------------------

# 12. Earnings Quality

Create an explicit earnings-quality section.

Possible checks:

``` text
profit_growth
cash_flow_conversion
receivables_growth
inventory_growth
margin_stability
other_income_dependency
exceptional_item_dependency
tax_rate_anomalies
```

Examples of red flags:

-   profits rise but cash flow does not
-   receivables rise faster than sales
-   inventory builds unexpectedly
-   profit growth is driven by exceptional items
-   other income contributes materially to earnings

------------------------------------------------------------------------

# 13. Valuation Engine

Do not rely on one valuation metric.

Use multiple lenses.

## Relative valuation

-   P/E
-   P/B
-   EV/EBITDA
-   EV/Sales
-   PEG
-   dividend yield

Compare against:

1.  own historical range
2.  sector median
3.  relevant peer group
4.  growth rate

## Intrinsic valuation where possible

Optional:

-   DCF
-   owner earnings
-   earnings power value

Do not create false precision.

Instead of:

> Fair value = ₹1,247.32

prefer:

> Estimated fair-value range = ₹1,150--₹1,350

and explain assumptions.

------------------------------------------------------------------------

# 14. Valuation Regimes

Classify:

``` text
Deeply Undervalued
Undervalued
Fairly Valued
Moderately Expensive
Expensive
Extremely Expensive
```

But valuation must be interpreted with growth.

Example:

A P/E of 40 can be reasonable for a company growing EPS 35% with high
ROCE.

A P/E of 18 can be expensive for a declining cyclical business.

------------------------------------------------------------------------

# 15. Peer Comparison

For every stock, compare against meaningful peers.

Example:

  Metric             Company   Peer Median
  ---------------- --------- -------------
  Revenue Growth         18%           12%
  PAT Growth             25%           14%
  ROCE                   24%           18%
  P/E                    32x           25x
  Debt/Equity            0.2           0.5

AI conclusion:

> The premium valuation is partly justified by superior growth and
> capital efficiency, but upside is less attractive at the current
> multiple.

------------------------------------------------------------------------

# 16. Sector Analysis

A stock cannot be analyzed in isolation.

Collect:

-   sector trend
-   industry growth
-   government policy
-   regulation
-   commodity inputs
-   interest-rate sensitivity
-   demand cycle
-   competitive intensity
-   capacity additions
-   sector valuation

Examples:

Bank:

-   credit growth
-   NIM
-   GNPA
-   NNPA
-   credit cost
-   CASA
-   ROA
-   ROE

IT:

-   deal wins
-   revenue growth
-   attrition
-   margins
-   USD/INR
-   client concentration

Manufacturing:

-   capacity utilization
-   order book
-   raw material prices
-   capex cycle

------------------------------------------------------------------------

# 17. News Intelligence

This should be a first-class component.

Do not feed random news directly to the LLM.

Create a news pipeline:

``` text
Collect
  ↓
Deduplicate
  ↓
Classify
  ↓
Score materiality
  ↓
Extract entities
  ↓
Extract event
  ↓
Determine impact
  ↓
Store structured event
  ↓
Send relevant events to LLM
```

------------------------------------------------------------------------

# 18. News Classification

Categories:

``` text
Earnings
Management
Order Win
Order Loss
M&A
Fund Raising
Debt
Regulation
Government Policy
Litigation
Promoter
Shareholding
Insider Trading
Credit Rating
Dividend
Buyback
Bonus
Split
Expansion
Capex
Product Launch
Partnership
Analyst Rating
Macro
Sector
Other
```

------------------------------------------------------------------------

# 19. News Materiality Score

Each news item should receive:

``` text
materiality_score: 0–100
```

Example:

### 90--100

Potentially thesis-changing.

### 70--89

Material.

### 40--69

Relevant but limited impact.

### 0--39

Low-value noise.

Only material/relevant news should strongly influence the
recommendation.

------------------------------------------------------------------------

# 20. News Sentiment Is Not Enough

Avoid simplistic:

> News sentiment = Positive

Instead calculate:

``` text
event_type
materiality
expected_duration
financial_impact
certainty
direction
```

Example:

> Company receives ₹500 crore order.

Better interpretation:

-   positive
-   materiality: 72
-   expected duration: medium
-   financial impact: potentially meaningful
-   certainty: high
-   impact: positive

But the system should still check:

-   order size relative to annual revenue
-   margin
-   execution period
-   whether order is already priced in

------------------------------------------------------------------------

# 21. Source Hierarchy

The AI should prioritize sources.

### Tier 1

-   company filings
-   exchange announcements
-   annual reports
-   investor presentations
-   earnings calls
-   official government/regulatory sources

### Tier 2

-   established financial publications
-   reputable financial databases
-   recognized research sources

### Tier 3

-   aggregators
-   blogs
-   forums
-   social media

Tier 3 should never override Tier 1 evidence.

------------------------------------------------------------------------

# 22. Corporate Actions

Track:

-   dividends
-   bonus
-   stock split
-   rights issue
-   buyback
-   merger
-   demerger
-   preferential issue
-   QIP
-   ESOP dilution

Corporate actions can materially change:

-   average cost
-   share count
-   valuation
-   ownership
-   thesis

------------------------------------------------------------------------

# 23. Promoter and Institutional Analysis

Where reliable data is available:

Analyze:

-   promoter holding trend
-   promoter pledging
-   FII holding
-   DII holding
-   mutual fund holding
-   insider buying/selling

Focus on trends rather than one quarter.

Example:

> Promoter ownership declined from 57% to 49% over six quarters.

This deserves attention even if the latest quarter looks normal.

------------------------------------------------------------------------

# 24. Technical Analysis Integration

Since Folio is a holdings advisor rather than a pure technical trading
system, technical analysis should be used as **timing/context**, not as
the sole investment thesis.

Include:

-   trend
-   support
-   resistance
-   EMA 20/50/200
-   RSI
-   MACD
-   VWAP where relevant
-   ATR
-   volume
-   relative strength
-   breakout/breakdown
-   drawdown
-   volatility

Useful derived states:

``` text
LONG_TERM_TREND
MEDIUM_TERM_TREND
SHORT_TERM_TREND
MOMENTUM
VOLATILITY
SUPPORT_ZONE
RESISTANCE_ZONE
```

Technical analysis should answer:

> "Is now a good time to add/reduce?"

rather than:

> "Is this a good company?"

------------------------------------------------------------------------

# 25. Technical Evidence Rules

Avoid using:

> RSI = 72 → SELL

Instead:

> RSI is elevated, indicating strong momentum. Combined with price
> extension above major moving averages and nearby resistance, immediate
> fresh buying has poor risk/reward. Existing holders can continue
> holding with a trailing risk framework.

------------------------------------------------------------------------

# 26. Position-Level Analysis

For each holding calculate:

``` text
invested_amount
current_value
absolute_pnl
pnl_percent
portfolio_weight
days_held
distance_from_average
distance_from_stop_loss
distance_from_target
distance_from_support
distance_from_resistance
```

------------------------------------------------------------------------

# 27. Position Sizing Analysis

This is critical.

Example:

``` text
Stock A = 4%
Stock B = 7%
Stock C = 19%
```

Even if Stock C is excellent:

> 19% concentration may justify HOLD rather than BUY.

Folio should define configurable limits.

Example defaults:

``` text
single_stock_warning = 10%
single_stock_high_risk = 15%

sector_warning = 25%
sector_high_risk = 35%
```

These are configurable and should not be presented as universal
financial rules.

------------------------------------------------------------------------

# 28. Portfolio Diversification

Analyze exposure by:

-   sector
-   industry
-   market cap
-   geography
-   business model
-   cyclicality
-   factor
-   theme

Potential factor exposure:

-   momentum
-   value
-   growth
-   quality
-   small-cap
-   PSU
-   defence
-   manufacturing
-   financials

------------------------------------------------------------------------

# 29. Correlation Analysis

Where historical price data exists:

Calculate:

-   correlation matrix
-   rolling correlation
-   sector correlation

Flag:

> Portfolio appears diversified by stock count but concentrated by
> underlying risk factor.

This is much more useful than simply counting stocks.

------------------------------------------------------------------------

# 30. Portfolio Drawdown & Risk

Track:

-   portfolio volatility
-   max drawdown
-   current drawdown
-   stock contribution to drawdown
-   sector contribution
-   concentration risk

Answer:

> "Which holdings are causing most of the portfolio risk?"

------------------------------------------------------------------------

# 31. Recommendation Taxonomy

Do not restrict output to BUY / HOLD / SELL.

Recommended actions:

``` text
STRONG_BUY
BUY
ACCUMULATE
HOLD
HOLD_WAIT_FOR_CORRECTION
HOLD_TRAIL_STOP
REDUCE
STRONG_REDUCE
EXIT
WATCH
```

For simplicity, UI can group them into:

``` text
BUY
HOLD
REDUCE
EXIT
```

while retaining the detailed internal action.

------------------------------------------------------------------------

# 32. Recommendation Must Be Conditional

Every recommendation should include:

### Current action

> HOLD

### Why

> Fundamentals remain strong and valuation is reasonable, but price is
> extended.

### What would change the view

> Add if price corrects into ₹X--₹Y and earnings trajectory remains
> intact.

### Risk trigger

> Reduce if earnings growth deteriorates for two consecutive quarters or
> the key support breaks with material negative news.

This makes the system substantially more useful.

------------------------------------------------------------------------

# 33. Buy More Logic

The LLM should evaluate at least:

``` text
business_quality
earnings_momentum
valuation
technical_setup
portfolio_weight
risk_reward
investment_horizon
recent_news
thesis_integrity
```

Only recommend ADD/BUY when enough conditions align.

Example:

> Strong business + improving earnings + reasonable valuation +
> acceptable portfolio weight + favorable entry = ACCUMULATE.

------------------------------------------------------------------------

# 34. Reduce Logic

Potential triggers:

-   thesis deterioration
-   valuation excess
-   deteriorating fundamentals
-   excessive position size
-   sector concentration
-   major negative event
-   governance concern
-   deteriorating cash flow
-   balance-sheet deterioration

Importantly:

> A stock falling 20% is not automatically a reason to sell.

Likewise:

> A stock rising 50% is not automatically a reason to book profit.

------------------------------------------------------------------------

# 35. Stop-Loss Interpretation

Distinguish:

### Trading stop

Technical invalidation.

### Investment thesis stop

Fundamental deterioration.

### Portfolio risk stop

Position becomes too risky/large.

These should not be conflated.

For a long-term holding, a temporary technical breakdown may not
invalidate the fundamental thesis.

------------------------------------------------------------------------

# 36. Target Price Handling

A manually entered target should be treated as:

``` text
USER_TARGET
```

not as truth.

Folio should compare:

``` text
user_target
valuation_range
analyst_estimates
technical_resistance
AI_estimated_range
```

Then explain discrepancies.

Example:

> Your target is ₹1,500. Current fundamental valuation suggests
> ₹1,250--₹1,400, while technical resistance is around ₹1,350. The
> target therefore appears aggressive under current assumptions.

------------------------------------------------------------------------

# 37. Investment Thesis Tracking

This is a powerful feature.

Allow the user to write:

> "I bought this because I expect strong defence order growth over the
> next 3 years."

Store this as a structured thesis.

Then periodically evaluate:

``` text
THESIS_VALID
THESIS_STRENGTHENING
THESIS_WEAKENING
THESIS_INVALIDATED
```

The AI should explicitly answer:

> "Is the original reason for owning this stock still valid?"

This is more valuable than reacting to price movements.

------------------------------------------------------------------------

# 38. AI Analysis Architecture

Do not send the entire portfolio and all raw web content to one LLM
call.

Use a multi-stage pipeline.

``` text
                DATA SOURCES
                     │
                     ▼
              Data Ingestion
                     │
                     ▼
              Normalization
                     │
                     ▼
            Evidence Extraction
                     │
        ┌────────────┼─────────────┐
        ▼            ▼             ▼
   Fundamentals   Technicals      News
        │            │             │
        └────────────┼─────────────┘
                     ▼
              Stock Analysis
                     │
                     ▼
             Portfolio Analysis
                     │
                     ▼
             Recommendation
                     │
                     ▼
             Risk / Validation
                     │
                     ▼
                Final Report
```

------------------------------------------------------------------------

# 39. Recommended LLM Roles

Use separate prompts/agents rather than one huge prompt.

## Agent 1 --- Fundamental Analyst

Analyzes:

-   business
-   financials
-   growth
-   profitability
-   debt
-   cash flow
-   valuation

Output structured JSON.

## Agent 2 --- Technical Analyst

Analyzes:

-   trend
-   momentum
-   support/resistance
-   entry timing
-   risk levels

## Agent 3 --- News Analyst

Analyzes:

-   material events
-   positive/negative impact
-   duration
-   thesis impact

## Agent 4 --- Portfolio Analyst

Analyzes:

-   allocation
-   concentration
-   diversification
-   correlation
-   risk

## Agent 5 --- Investment Committee / Final Analyst

Receives outputs from all previous agents.

Its job is to:

-   reconcile conflicts
-   prioritize evidence
-   produce final recommendation

------------------------------------------------------------------------

# 40. Evidence-First LLM Prompting

The final LLM should receive a structured package like:

``` json
{
  "security": {},
  "position": {},
  "fundamentals": {},
  "valuation": {},
  "technical": {},
  "news": [],
  "corporate_actions": [],
  "sector": {},
  "portfolio_context": {},
  "user_thesis": {},
  "market_context": {},
  "data_quality": {}
}
```

The model should be explicitly instructed:

1.  Never invent missing data.
2.  Distinguish fact from inference.
3.  Cite evidence IDs.
4.  Prefer recent primary sources.
5.  Explain conflicting evidence.
6.  Penalize stale data.
7.  Do not treat sentiment as fact.
8.  Do not make guaranteed-return statements.
9.  Consider portfolio context before recommending additional capital.
10. State uncertainty.

------------------------------------------------------------------------

# 41. Structured LLM Output

Require JSON output.

Example schema:

``` json
{
  "symbol": "XYZ",
  "overall_rating": "HOLD",
  "action": "HOLD_WAIT_FOR_CORRECTION",
  "confidence": 78,

  "business_quality_score": 82,
  "fundamental_score": 76,
  "valuation_score": 61,
  "technical_score": 71,
  "news_score": 68,
  "portfolio_fit_score": 55,

  "thesis_status": "VALID",

  "recommendation_summary": "",
  "bull_case": "",
  "base_case": "",
  "bear_case": "",

  "key_reasons": [],
  "key_risks": [],

  "buy_conditions": [],
  "reduce_conditions": [],
  "exit_conditions": [],

  "support_levels": [],
  "resistance_levels": [],

  "fair_value_range": {
    "low": null,
    "base": null,
    "high": null
  },

  "evidence_ids": [],
  "data_quality": "GOOD"
}
```

------------------------------------------------------------------------

# 42. Confidence Is Not Probability of Profit

Do not allow the UI to say:

> 85% chance stock will rise.

Instead:

> Analysis confidence: 85/100

Confidence means:

> How strongly the available evidence supports the analysis.

It should depend on:

-   source quality
-   data completeness
-   consistency
-   recency
-   number of independent supporting signals

------------------------------------------------------------------------

# 43. Scoring Model

Use deterministic scoring alongside LLM reasoning.

Example:

``` text
Fundamental Quality       20%
Growth                    15%
Profitability             10%
Balance Sheet             10%
Cash Flow                 10%
Valuation                 15%
Technical Context         10%
News / Events              5%
Portfolio Fit              5%
```

These weights should be configurable.

Do not blindly use the weighted score as the recommendation.

The score is a **decision-support signal**.

The LLM is responsible for contextual reasoning.

------------------------------------------------------------------------

# 44. Quality Gates

Before producing a recommendation:

### Gate 1 --- Data completeness

If essential financial data is missing:

> LOW_CONFIDENCE

### Gate 2 --- Data freshness

If critical data is stale:

> STALE_DATA

### Gate 3 --- Source reliability

If evidence is primarily low-quality sources:

> LOW_SOURCE_CONFIDENCE

### Gate 4 --- Conflicting evidence

If signals conflict:

> MIXED_SIGNAL

### Gate 5 --- Portfolio constraint

If stock is already oversized:

> PORTFOLIO_CONCENTRATION

------------------------------------------------------------------------

# 45. Evidence Ledger

Every important AI conclusion should link to evidence.

Example:

``` text
Conclusion:
"Cash-flow quality is deteriorating."

Evidence:
E102 — CFO declined 32% YoY
E103 — PAT increased 14% YoY
E104 — Receivables increased 27% YoY
```

This enables the user to ask:

> "Why are you saying this?"

and Folio can answer transparently.

------------------------------------------------------------------------

# 46. Citation Requirements

Every external fact used in an AI analysis should ideally have:

``` text
source_name
source_url
published_at
retrieved_at
source_type
evidence_text
```

The frontend should allow the user to click through to the source.

------------------------------------------------------------------------

# 47. Contradiction Detection

Build a contradiction checker.

Examples:

### Source A

> Revenue expected to grow strongly.

### Company filing

> Management guides to muted demand.

Flag:

``` text
CONFLICTING_EVIDENCE
```

The final analyst must resolve or explicitly acknowledge the conflict.

------------------------------------------------------------------------

# 48. Scenario Analysis

Every meaningful holding should have:

## Bull case

What must happen for upside?

## Base case

Most reasonable outcome.

## Bear case

What can go wrong?

Example:

``` text
Bull:
Earnings CAGR 25%, multiple remains stable.

Base:
Earnings CAGR 15%, valuation normalizes.

Bear:
Margins compress + growth slows + multiple contracts.
```

------------------------------------------------------------------------

# 49. Thesis Invalidation

This is one of the most important outputs.

For every holding:

``` text
Thesis remains valid if:
- Revenue growth remains > X
- ROCE remains > Y
- debt remains below Z
- order book remains healthy

Thesis weakens if:
- margins decline for 2 quarters
- cash conversion deteriorates
- promoter pledge increases

Thesis invalidated if:
- major governance issue
- structural business deterioration
- balance sheet stress
```

These thresholds should be dynamically derived where possible rather
than hard-coded universally.

------------------------------------------------------------------------

# 50. Portfolio Recommendation

After stock-level analysis, create a portfolio-level recommendation.

Example:

``` text
PORTFOLIO ACTIONS

1. ADD:
   Stock A
   Reason: strong fundamentals + underweight

2. HOLD:
   Stock B
   Reason: strong company but fully valued

3. REDUCE:
   Stock C
   Reason: 17% portfolio weight + weakening thesis

4. EXIT:
   Stock D
   Reason: thesis invalidated
```

Then answer:

> "If I have ₹50,000 available, where should it go?"

The engine should allocate by **risk-adjusted attractiveness and
portfolio need**, not simply highest stock score.

------------------------------------------------------------------------

# 51. Capital Allocation Engine

Optional but highly valuable.

Input:

``` text
available_cash
minimum_cash_buffer
portfolio_weights
stock_scores
valuation
risk
correlation
```

Output:

``` text
recommended_allocation
```

Example:

  Stock   Action                Suggested Allocation
  ------- ------------------- ----------------------
  A       ACCUMULATE                         ₹20,000
  B       HOLD                                    ₹0
  C       ADD ON CORRECTION                  ₹10,000
  D       REDUCE                                  \-

Always present this as a recommendation, not an instruction.

------------------------------------------------------------------------

# 52. Avoid LLM Hallucinations

Implement explicit safeguards.

The model must never:

-   invent financial figures
-   invent news
-   invent analyst targets
-   invent company guidance
-   invent source URLs
-   claim to have accessed a source it did not receive
-   treat unavailable data as zero
-   extrapolate missing data without saying so

Prompt:

> If a required fact is unavailable, explicitly return null/unknown
> rather than estimating it unless estimation is explicitly requested.

------------------------------------------------------------------------

# 53. Data Quality Score

Calculate independently of the LLM.

Example:

``` text
Data completeness       30%
Data freshness          20%
Primary-source coverage 20%
Cross-source agreement  15%
Historical coverage     15%
```

Result:

``` text
92 = Excellent
80 = Good
65 = Moderate
<50 = Poor
```

The UI should show this prominently.

------------------------------------------------------------------------

# 54. Analysis Timestamp

Every report must clearly show:

``` text
Analysis generated:
18-Aug-2026 21:05 IST

Market data through:
18-Aug-2026 close

Latest financial results:
Quarter ended Jun-2026

News checked through:
18-Aug-2026 20:45 IST
```

This prevents users from assuming the report is live when it is not.

------------------------------------------------------------------------

# 55. Analysis Versioning

Store:

``` text
analysis_run_id
prompt_version
model_name
model_version
data_snapshot_id
analysis_timestamp
```

This allows:

> "Why did Folio's recommendation change from HOLD to REDUCE?"

The system can compare previous and current evidence.

------------------------------------------------------------------------

# 56. Recommendation Change Detection

Track transitions:

``` text
BUY → HOLD
HOLD → BUY
HOLD → REDUCE
BUY → REDUCE
REDUCE → EXIT
```

When recommendation changes, explain:

``` text
Previous:
HOLD

Current:
REDUCE

Primary reasons:
1. Earnings downgrade
2. Valuation expansion
3. Portfolio weight increased
```

------------------------------------------------------------------------

# 57. Alert System

Potential alerts:

### Fundamental

-   earnings deterioration
-   debt increase
-   cash flow deterioration
-   margin compression

### News

-   major regulatory event
-   promoter event
-   order cancellation
-   management resignation
-   fraud/governance allegation

### Technical

-   major support break
-   trend reversal
-   unusual volume

### Portfolio

-   position exceeds weight limit
-   sector concentration increases
-   portfolio drawdown threshold

------------------------------------------------------------------------

# 58. UI --- Portfolio Dashboard

Recommended top section:

``` text
Portfolio Value
Invested
Today's P&L
Total P&L
Cash
Portfolio Risk
Diversification Score
```

Then:

``` text
AI Portfolio Health: 78/100
```

------------------------------------------------------------------------

# 59. Portfolio AI Summary

Example:

> **Overall: HEALTHY WITH MODERATE CONCENTRATION**

Then:

### Positive

-   Earnings quality improving
-   Majority of holdings profitable
-   Low leverage exposure

### Concerns

-   Financial sector overweight
-   Two holdings account for 31% of portfolio
-   Three stocks are trading above historical valuation

### Priority

> Review Stock X and Stock Y before deploying additional capital.

------------------------------------------------------------------------

# 60. Holdings Table

Columns:

``` text
Stock
Qty
Avg Price
LTP
P&L
Weight
AI View
Fundamental Score
Technical State
Risk
Action
```

Use clear status badges.

------------------------------------------------------------------------

# 61. Stock Detail Page

Suggested structure:

``` text
Company Header
↓
Position Summary
↓
AI Recommendation
↓
Why?
↓
Thesis Status
↓
Fundamental Scorecard
↓
Valuation
↓
Technical View
↓
News
↓
Corporate Actions
↓
Peer Comparison
↓
Bull / Base / Bear
↓
Risks
↓
Buy / Reduce Conditions
↓
Evidence & Sources
↓
Historical AI Recommendations
```

------------------------------------------------------------------------

# 62. AI Recommendation UI

Example:

``` text
HOLD — WAIT FOR BETTER ENTRY

Confidence: 82/100

Why:
✓ Earnings growth remains strong
✓ Balance sheet is healthy
✓ Sector outlook is positive
⚠ Valuation is above historical average
⚠ Price is near major resistance
⚠ Portfolio already has 9.8% exposure

Suggested approach:
Continue holding.
Do not chase at current price.
Consider adding if valuation/technical setup improves.
```

------------------------------------------------------------------------

# 63. User Override

The user should always be able to override AI recommendations.

Example:

``` text
AI: REDUCE
User: KEEP

Reason:
"I am holding this for a 5-year thesis."
```

Folio should remember this and incorporate it into future analysis.

------------------------------------------------------------------------

# 64. Explainability

Every recommendation should answer five questions:

1.  What is your recommendation?
2.  Why?
3.  What evidence supports it?
4.  What could make this wrong?
5.  What should I watch next?

This should be a hard requirement.

------------------------------------------------------------------------

# 65. "What Changed?" Feature

One of the most useful features.

Instead of rerunning a report and showing everything again:

``` text
WHAT CHANGED SINCE LAST ANALYSIS?

• Quarterly PAT +18%
• Stock +7.2%
• P/E expanded from 24x → 28x
• New ₹800 crore order announced
• Promoter holding unchanged
• Technical trend improved
```

Then:

> Recommendation changed from HOLD → ACCUMULATE because earnings
> improved while valuation remains acceptable.

------------------------------------------------------------------------

# 66. Periodic Analysis

Recommended modes:

### Quick daily scan

-   price
-   technicals
-   major news
-   alerts

### Weekly portfolio review

-   price trend
-   news
-   portfolio changes
-   major risk

### Quarterly deep review

-   results
-   valuation
-   fundamentals
-   thesis
-   recommendation

### Event-driven review

Triggered by:

-   quarterly results
-   major announcement
-   large price movement
-   corporate action

------------------------------------------------------------------------

# 67. LLM Cost Optimization

Do not send expensive deep analysis every day.

Use:

``` text
cheap model / deterministic rules
        ↓
detect meaningful change
        ↓
deep LLM analysis only if required
```

Example triggers:

``` text
price move > 5%
major news
quarterly results
recommendation change
technical regime change
fundamental metric deterioration
```

------------------------------------------------------------------------

# 68. Model Abstraction

Implement:

``` python
class LLMProvider:
    async def analyze(self, prompt, schema): ...
```

Possible providers:

``` text
Gemini
OpenAI
Anthropic
Open-source model
Local model
```

The business logic should not depend on one provider.

------------------------------------------------------------------------

# 69. Prompt Versioning

Store prompts in files:

``` text
prompts/
    fundamental_analyst_v1.md
    technical_analyst_v1.md
    news_analyst_v1.md
    portfolio_analyst_v1.md
    final_investment_committee_v1.md
```

Never embed large prompts directly into Python code.

------------------------------------------------------------------------

# 70. Backend Architecture

Recommended structure:

``` text
app/
├── main.py
├── api/
│   ├── holdings.py
│   ├── portfolio.py
│   ├── analysis.py
│   ├── news.py
│   └── alerts.py
│
├── services/
│   ├── market_data/
│   ├── fundamentals/
│   ├── news/
│   ├── technicals/
│   ├── valuation/
│   ├── portfolio/
│   ├── analysis/
│   └── llm/
│
├── models/
├── schemas/
├── repositories/
├── prompts/
├── jobs/
├── config/
└── utils/
```

------------------------------------------------------------------------

# 71. Asynchronous Analysis

Deep portfolio analysis may take time.

Do not block the API request.

Recommended:

``` text
POST /analysis/portfolio
        ↓
create analysis_run
        ↓
queue job
        ↓
return run_id
```

Frontend:

``` text
GET /analysis/{run_id}
```

or WebSocket/SSE for progress.

------------------------------------------------------------------------

# 72. Analysis Job Stages

Example:

``` text
CREATED
FETCHING_MARKET_DATA
FETCHING_FUNDAMENTALS
FETCHING_NEWS
PROCESSING_TECHNICALS
BUILDING_EVIDENCE
ANALYZING_STOCKS
ANALYZING_PORTFOLIO
FINAL_RECONCILIATION
VALIDATING
COMPLETED
```

If something fails:

``` text
PARTIAL_COMPLETION
```

Never silently fail.

------------------------------------------------------------------------

# 73. Caching

Cache external data aggressively according to freshness.

Examples:

``` text
LTP: seconds/minutes
OHLCV: daily
Financials: until new result
Company profile: days
News: minutes
Peer data: daily
```

This reduces:

-   API costs
-   latency
-   rate-limit problems

------------------------------------------------------------------------

# 74. Database Strategy

### SQLite

Good for:

-   local development
-   single-user desktop/local deployment
-   testing

### PostgreSQL / Neon

Recommended production DB.

Use SQLAlchemy/SQLModel or equivalent abstraction so database switching
remains manageable.

------------------------------------------------------------------------

# 75. API Design

Suggested endpoints:

``` text
GET    /portfolio
POST   /holdings
PUT    /holdings/{id}
DELETE /holdings/{id}

GET    /holdings/{id}
GET    /holdings/{id}/analysis

POST   /analysis/portfolio
POST   /analysis/holding/{id}

GET    /analysis/{run_id}
GET    /analysis/{run_id}/evidence

GET    /news/{symbol}
GET    /fundamentals/{symbol}
GET    /technicals/{symbol}

GET    /portfolio/risk
GET    /portfolio/allocation
GET    /portfolio/changes
```

------------------------------------------------------------------------

# 76. Security

Even for a single-user application:

-   encrypt API keys
-   never expose provider keys to frontend
-   use environment variables/secrets manager
-   validate all external inputs
-   rate-limit expensive endpoints
-   protect analysis endpoints
-   log errors without leaking credentials

------------------------------------------------------------------------

# 77. Logging

Log:

``` text
request_id
analysis_run_id
symbol
provider
model
latency
token_usage
source_count
errors
```

Never log:

-   API keys
-   credentials
-   private tokens

------------------------------------------------------------------------

# 78. Testing Strategy

## Unit tests

Test:

-   P&L
-   allocation
-   valuation calculations
-   technical indicators
-   data normalization
-   freshness
-   recommendation mapping

## Integration tests

Test:

``` text
market provider → normalization → DB
news provider → classifier → DB
fundamentals → evidence builder
```

## LLM tests

Use fixed evidence packs.

Test whether the model:

-   hallucinates
-   ignores evidence
-   overweights news
-   gives unsupported targets
-   contradicts portfolio constraints

------------------------------------------------------------------------

# 79. LLM Evaluation Dataset

Create a benchmark set of real/historical cases.

Examples:

``` text
Strong fundamentals + expensive valuation
Weak fundamentals + cheap valuation
Strong stock + oversized position
Good company + bad sector
Bad company + temporary technical rally
Positive news + already priced in
Negative news + thesis unaffected
Conflicting financial indicators
Missing data
Stale data
```

Evaluate output against expected reasoning.

------------------------------------------------------------------------

# 80. Recommendation Stability Test

Do not allow tiny changes to produce wild recommendation changes.

Example:

``` text
Yesterday:
HOLD

Today:
BUY
```

should require a meaningful evidence change.

Implement:

``` text
recommendation_change_threshold
```

and require an explicit explanation for major changes.

------------------------------------------------------------------------

# 81. Guard Against Confirmation Bias

The user may enter:

> "I believe this stock will become a multibagger."

Folio must not simply confirm it.

Prompt:

> Challenge the user's thesis. Search for disconfirming evidence and
> explicitly identify the strongest argument against owning the stock.

This is essential.

------------------------------------------------------------------------

# 82. Bull/Bear Balance

Force the model to produce:

``` text
Strongest Bull Argument
Strongest Bear Argument
```

Then:

``` text
Which side currently has stronger evidence?
```

This produces much better analysis than generic sentiment.

------------------------------------------------------------------------

# 83. Avoid Price Anchoring

Do not allow:

> Average buy price = ₹900

to influence fundamental valuation.

The AI should treat average price as relevant to the user's P&L and
decision context, but not as evidence that ₹900 is fair value.

Example:

> "Your average price is ₹900, but the company's intrinsic valuation
> does not depend on your purchase price."

------------------------------------------------------------------------

# 84. Avoid Loss Aversion

Similarly:

> "I am down 25%."

must not automatically produce:

> HOLD until breakeven.

The AI should ask:

> "Would you buy this stock today at the current price?"

This is a powerful decision test.

------------------------------------------------------------------------

# 85. Fresh-Capital Test

For every holding, calculate conceptually:

> If I had fresh cash today, would this stock be one of the best uses of
> that cash?

Possible answers:

``` text
YES — ATTRACTIVE
YES — BUT WAIT FOR PRICE
NEUTRAL
NO — BETTER ALTERNATIVES
```

This helps prevent emotional attachment to existing positions.

------------------------------------------------------------------------

# 86. Opportunity-Cost Analysis

Portfolio recommendations should consider alternatives.

If:

``` text
Stock A expected risk-adjusted attractiveness = high
Stock B = medium
Stock C = low
```

and the user has limited cash:

> Buying A may be preferable to averaging down B.

This is much more useful than analyzing each holding independently.

------------------------------------------------------------------------

# 87. Exit Quality

When recommending REDUCE/EXIT, explain:

``` text
Reason category:
FUNDAMENTAL
VALUATION
PORTFOLIO_RISK
TECHNICAL
NEWS
THESIS_INVALIDATION
OPPORTUNITY_COST
```

This lets the UI explain exactly why the recommendation exists.

------------------------------------------------------------------------

# 88. Final Portfolio Report

Recommended structure:

``` text
1. Executive Summary

2. Portfolio Health

3. Top 3 Stocks to Consider Adding

4. Stocks to Hold

5. Stocks to Reduce

6. Stocks Where Thesis Is Weakening

7. Stocks to Exit / Closely Review

8. Concentration Risks

9. Sector Exposure

10. Biggest Positive Developments

11. Biggest Risks

12. Available-Cash Deployment Suggestions

13. What Changed Since Last Review

14. Key Watchlist

15. Data Quality / Limitations

16. Sources
```

------------------------------------------------------------------------

# 89. Example Final Recommendation

``` text
XYZ — HOLD / ACCUMULATE ON CORRECTION

Overall Score: 78/100
Confidence: 84/100
Thesis: VALID

Position:
20 shares
Average: ₹900
LTP: ₹1,025
P&L: +13.9%
Portfolio Weight: 6.2%

Fundamentals:
Strong

Valuation:
Fair-to-slightly-expensive

Technical:
Positive but extended

News:
Neutral-to-positive

Portfolio Fit:
Good

Why HOLD:
• Revenue and earnings growth remain healthy.
• Balance sheet is strong.
• Sector outlook remains supportive.
• Current valuation leaves limited margin of safety.
• Price is extended from major support.

Action:
Continue holding.
Avoid chasing.
Consider adding only if valuation or technical setup improves.

Bull:
...

Base:
...

Bear:
...

Thesis invalidation:
...

Key things to monitor:
...
```

------------------------------------------------------------------------

# 90. Data Sources Strategy

Build source adapters instead of coupling the system to websites.

Potential categories:

### Market

-   broker APIs
-   exchange feeds
-   market-data APIs
-   yfinance where appropriate

### Company fundamentals

-   exchange filings
-   company investor-relations pages
-   annual reports
-   quarterly result filings
-   recognized financial-data providers

### News

-   financial news APIs
-   RSS feeds
-   company announcements
-   exchange announcements

### Corporate actions

-   exchange filings
-   company filings

### Macro

-   RBI
-   government sources
-   official statistical sources

The application should record exactly which source produced every
important data point.

------------------------------------------------------------------------

# 91. Free-vs-Paid Provider Abstraction

Start with free/low-cost sources where practical, but do not design the
architecture around one free source.

Create:

``` text
ProviderPriority

1. Primary source
2. Secondary source
3. Fallback source
```

Example:

``` python
fundamental_provider_chain = [
    ExchangeProvider(),
    CompanyFilingProvider(),
    SecondaryProvider()
]
```

If provider 1 fails, continue to provider 2.

------------------------------------------------------------------------

# 92. Data Reconciliation

When multiple sources provide the same metric:

``` text
Source A: P/E = 27.1
Source B: P/E = 27.4
Source C: P/E = 27.2
```

Do not arbitrarily choose one.

Store:

``` text
reported_value
source
calculation_method
as_of_date
```

If differences are small, mark:

``` text
RECONCILED
```

If materially different:

``` text
DATA_CONFLICT
```

and inform the LLM.

------------------------------------------------------------------------

# 93. Important Financial Metric Normalization

Normalize units:

``` text
₹ crore
₹ million
₹ lakh
₹ billion
```

Normalize:

``` text
YoY
QoQ
TTM
FY
CY
```

Never let the LLM infer units from ambiguous strings.

------------------------------------------------------------------------

# 94. TTM Metrics

Where possible calculate:

``` text
TTM Revenue
TTM EBITDA
TTM EBIT
TTM PAT
TTM CFO
TTM FCF
```

TTM is often more useful for current valuation than an old full-year
number.

------------------------------------------------------------------------

# 95. Financial Trend Engine

Calculate:

``` text
1Y growth
3Y CAGR
5Y CAGR

latest quarter growth
previous quarter growth
growth acceleration/deceleration
```

Example:

``` text
Revenue:
FY23 → FY24 → FY25 → FY26

PAT:
FY23 → FY24 → FY25 → FY26
```

The LLM should see the trajectory, not just the latest number.

------------------------------------------------------------------------

# 96. Management Quality

Where reliable evidence exists, evaluate:

-   capital allocation
-   guidance credibility
-   execution against previous guidance
-   related-party transactions
-   promoter actions
-   governance events
-   auditor qualifications
-   contingent liabilities

Do not make defamatory claims from unverified allegations.

Use careful wording:

> "A reported allegation requires verification."

------------------------------------------------------------------------

# 97. Risk Taxonomy

Every stock should have a structured risk list.

Categories:

``` text
VALUATION_RISK
BUSINESS_RISK
COMPETITIVE_RISK
BALANCE_SHEET_RISK
GOVERNANCE_RISK
REGULATORY_RISK
CYCLICAL_RISK
LIQUIDITY_RISK
EXECUTION_RISK
MACRO_RISK
CONCENTRATION_RISK
TECHNICAL_RISK
```

Each risk:

``` text
severity
probability
evidence
mitigation
```

------------------------------------------------------------------------

# 98. Market Regime

Portfolio recommendations should consider broader market conditions.

Track:

-   Nifty trend
-   Sensex trend
-   India VIX
-   breadth
-   sector rotation
-   interest-rate environment
-   liquidity
-   major macro events

Do not use market regime to override company fundamentals automatically.

Use it as a risk/context modifier.

------------------------------------------------------------------------

# 99. Recommendation Decision Tree

A useful conceptual flow:

``` text
Is the investment thesis valid?
        │
       NO ──→ EXIT / REDUCE
        │
       YES
        ↓
Are fundamentals improving/stable?
        │
       NO ──→ HOLD/REDUCE depending severity
        │
       YES
        ↓
Is valuation attractive?
        │
       NO ──→ HOLD / WAIT
        │
       YES
        ↓
Is portfolio weight acceptable?
        │
       NO ──→ HOLD
        │
       YES
        ↓
Is entry technically reasonable?
        │
       NO ──→ ACCUMULATE ON CORRECTION
        │
       YES
        ↓
BUY / ACCUMULATE
```

The actual implementation should use evidence and scores rather than
this literal deterministic tree.

------------------------------------------------------------------------

# 100. Implementation Phases

## Phase 1 --- Portfolio Core

Implement:

-   holdings
-   transactions
-   average cost
-   P&L
-   portfolio allocation
-   basic dashboard

## Phase 2 --- Market Data

Implement:

-   LTP
-   OHLCV
-   price history
-   technical indicators

## Phase 3 --- Fundamentals

Implement:

-   financial statements
-   ratios
-   TTM
-   growth
-   profitability
-   debt
-   cash flow

## Phase 4 --- News Intelligence

Implement:

-   news ingestion
-   deduplication
-   classification
-   materiality
-   source tracking

## Phase 5 --- AI Stock Analyst

Implement:

-   evidence pack
-   fundamental agent
-   technical agent
-   news agent
-   final recommendation

## Phase 6 --- Portfolio Intelligence

Implement:

-   concentration
-   diversification
-   correlation
-   sector exposure
-   capital allocation

## Phase 7 --- Thesis Tracking

Implement:

-   user thesis
-   thesis status
-   thesis invalidation
-   change detection

## Phase 8 --- Alerts

Implement:

-   price alerts
-   fundamental alerts
-   news alerts
-   recommendation changes

## Phase 9 --- Evaluation

Implement:

-   LLM benchmark
-   hallucination testing
-   recommendation consistency
-   historical replay

------------------------------------------------------------------------

# 101. MVP Scope

Do not build everything initially.

MVP should include:

### Portfolio

-   holdings
-   quantity
-   average price
-   LTP
-   P&L
-   portfolio weight

### Market

-   daily OHLCV
-   basic technicals

### Fundamentals

-   revenue
-   PAT
-   EPS
-   ROE
-   ROCE
-   debt
-   cash flow
-   P/E
-   market cap

### News

-   recent material news

### AI

-   stock analysis
-   portfolio summary
-   BUY/HOLD/REDUCE/EXIT
-   reasons
-   risks
-   bull/base/bear
-   thesis validity
-   evidence/source links

Everything else can follow.

------------------------------------------------------------------------

# 102. Most Important Product Principle

The goal is not:

> "Make the AI predict stock prices."

The goal is:

> **"Help the investor make better decisions with the position they
> already own."**

That means the system should emphasize:

-   business quality
-   valuation
-   thesis integrity
-   risk
-   portfolio construction
-   opportunity cost
-   evidence
-   uncertainty

rather than price prediction.

------------------------------------------------------------------------

# 103. Final AI System Prompt --- Recommended Principles

The final investment committee model should be instructed approximately
as follows:

``` text
You are the senior investment committee analyst for Folio.

Your job is to analyze an investor's existing equity portfolio using only the evidence supplied to you.

You are not a price-prediction engine.

You must evaluate:
1. Business quality
2. Financial performance
3. Earnings quality
4. Balance sheet
5. Cash flow
6. Valuation
7. Sector conditions
8. Recent material news
9. Corporate actions
10. Technical context
11. Portfolio concentration
12. User's investment horizon
13. Original investment thesis
14. Opportunity cost

Rules:

- Never invent facts.
- Never invent sources.
- Never treat missing data as zero.
- Clearly distinguish facts, calculations, inference and opinion.
- Prefer primary sources.
- Give greater weight to recent material evidence.
- Explicitly identify stale or conflicting data.
- Challenge the user's thesis rather than confirming it.
- Do not anchor valuation to the user's purchase price.
- Do not recommend averaging down merely because the position is losing money.
- Do not recommend selling merely because the stock price has fallen.
- Do not recommend buying merely because momentum is strong.
- Consider whether additional capital would improve the portfolio.
- Explain what would invalidate the thesis.
- Provide bull, base and bear scenarios.
- State uncertainty and confidence.
- Every material conclusion must be traceable to evidence.
- Recommendations are decision-support, not guaranteed outcomes.

For every holding, answer:

1. What is the current recommendation?
2. Why?
3. Is the investment thesis still valid?
4. Is the company fundamentally attractive?
5. Is the valuation attractive?
6. Is the current price a good entry point?
7. Is the current portfolio allocation appropriate?
8. What are the strongest risks?
9. What would make you change the recommendation?
10. What should the investor monitor next?
```

------------------------------------------------------------------------

# 104. Definition of Done

Folio's AI portfolio advisor should be considered production-ready only
when:

-   [ ] Every recommendation is backed by structured evidence.
-   [ ] External facts have source and timestamp metadata.
-   [ ] Data freshness is visible.
-   [ ] Missing data is explicitly handled.
-   [ ] Conflicting data is detected.
-   [ ] The AI cannot fabricate sources or financial metrics.
-   [ ] Stock analysis considers fundamentals + valuation + technicals +
    news.
-   [ ] Portfolio analysis considers concentration and diversification.
-   [ ] User investment horizon is incorporated.
-   [ ] User's original thesis is incorporated and challenged.
-   [ ] Recommendations are conditional and explainable.
-   [ ] Bull/base/bear scenarios are available.
-   [ ] Thesis invalidation conditions are provided.
-   [ ] Previous recommendations can be compared.
-   [ ] "What changed?" is supported.
-   [ ] LLM model/provider is replaceable.
-   [ ] Prompt versions are stored.
-   [ ] Analysis runs are auditable.
-   [ ] Data providers are replaceable.
-   [ ] The system handles provider failure gracefully.
-   [ ] LLM hallucination tests exist.
-   [ ] Recommendation consistency tests exist.
-   [ ] The UI clearly distinguishes AI analysis from verified market
    facts.
-   [ ] The system does not present guaranteed returns or certainty.

------------------------------------------------------------------------

# 105. Recommended End State

The ideal Folio experience should feel less like:

> "Ask an AI whether my stocks will go up."

and more like:

> **"Give me an investment committee review of my portfolio based on the
> latest available evidence."**

The user should be able to open Folio and immediately see:

``` text
YOUR PORTFOLIO

Overall Health: 81/100

What looks good:
✓ 7 holdings have improving earnings
✓ Balance-sheet risk is low
✓ 5 holdings have attractive long-term fundamentals

What needs attention:
⚠ Financial sector concentration is high
⚠ 2 stocks are significantly above historical valuation
⚠ 1 holding has a weakening investment thesis

If deploying ₹50,000 today:
1. Stock A — ACCUMULATE
2. Stock B — WAIT FOR CORRECTION
3. Stock C — DO NOT ADD
4. Stock D — REVIEW / REDUCE

Most important change:
Stock X moved from HOLD → REDUCE because
earnings quality deteriorated and valuation remains elevated.

Next review:
Quarterly results / major company event / material news.
```

That is the product direction that will make Folio materially more
useful than a generic AI stock-chat application.
