# Plan: "Ask AI" Chatbox Feature

## Overview

Add a chatbox to the **AI Advisor** page (portfolio context) and the **holding detail**
page (per-stock context). The chat uses the **same LLM provider** as the holdings
analyzer (`get_llm_provider()` -> mock/OpenAI/Gemini). The model acts as a highly
experienced financial analyst that answers questions grounded in the **previously
generated analysis** (`Recommendation` rows + evidence) and the user's **holdings data**.

Conversations are kept in **browser session state only** (no DB persistence).

### Decisions (confirmed with user)

1. **Chat history**: session only (frontend state) - no DB tables/migration.
2. **Response delivery**: simple request/response (non-streaming).
3. **Context source**: stored analysis + holdings (no live re-fetch per question).
4. **Chat scope**: per-context thread - one conversation per stock / per portfolio
   within the current browser session.
5. **Analysis requirement**: chat requires prior analysis to exist (**Option B**).
   If no analysis exists for a context, the chatbox is disabled and prompts the user
   to run analysis first. Backend returns 404 in that case.

---

## Backend

### 1. New endpoint: `POST /analysis/chat`

File: `backend/app/routers/analysis.py`

Request body (new Pydantic schema in `schemas.py`):

```json
{
  "context": "holding" | "portfolio",
  "holdingId": "uuid (required when context=holding)",
  "message": "string (1..2000 chars)",
  "history": [ { "role": "user" | "assistant", "content": "string" } ]
}
```

Response:

```json
{ "reply": "string", "provider": "mock", "modelName": "mock-analyzer-v1" }
```

Handler logic:

- Auth via `get_current_user`; every query scoped by `user_id` (multi-user privacy rule).
- If `context=holding`:
  - Load holding via `_get_owned_holding()` (404 if not owned).
  - Load latest `Recommendation` (kind=holding, holding_id). If none -> **404**
    ("No analysis available for this holding yet").
- If `context=portfolio`:
  - Load latest portfolio `Recommendation` + latest per-symbol holding recommendations
    + all holdings + `InvestmentProfile`.
  - If no portfolio recommendation AND no per-symbol recommendations -> **404**
    ("No portfolio analysis available yet").
- Validate/truncate: reject empty message, cap message length (2000), cap history to
  last **10** messages, cap each history content length (2000).
- Get provider via `get_llm_provider()` (same as analysis). Wrap `LLMProviderError`
  -> 400/502 like `_provider_meta()`.
- Call `provider.generate_text(...)` (NOT `generate_json` - replies are free-form
  text). `generate_text` already applies the existing LLM rate limiter for non-mock.
- Return `{ reply, provider, modelName }`.

### 2. New service module: `backend/app/services/analysis/chat.py`

- `build_chat_context(...)` - assembles a compact JSON context dict from the
  Recommendation + holdings + profile. Reuse the shape of existing evidence where
  cheap, keep it compact to fit the token budget:
  - **holding context:** symbol, position snapshot (qty, avg price, LTP, P/L,
    stop/target), the recommendation (rating, action, confidence, scores, thesis,
    summary, why, bull/base/bear cases, key reasons/risks, buy/reduce/exit conditions,
    support/resistance, fair value range, data quality), evidence items (trimmed),
    investment profile.
  - **portfolio context:** portfolio recommendation (health score, positives, concerns,
    priority, summary) + per-symbol rows (symbol, rating, action, confidence, summary)
    + holdings summary + profile.
- `render_chat_prompt(context, history, question)` - serializes to JSON, appends
  history and the user's question.
- Constants: `MAX_HISTORY`, `MAX_MESSAGE_CHARS`, `MAX_CONTEXT_...` to bound tokens.

### 3. New prompt file: `backend/app/prompts/chat_advisor_v1.md`

Persona: a **highly experienced financial analyst** for Indian (NSE/BSE) markets.
Rules:

- Reason **only** from the provided context (holdings + previously generated analysis
  + evidence).
- Answer the specific question concisely and clearly; reference the numbers/ratings
  in context.
- If the question can't be answered from context, say so rather than inventing facts.
- Note data quality / staleness when relevant.
- Plain text/markdown, not JSON.
- Standard disclaimer footer (not investment advice).

### 4. Mock provider support: `backend/app/services/llm/mock_provider.py`

Add a `chat` branch in `generate_text`, detected via a marker (e.g. `<<AGENT:chat>>`)
placed in the chat system prompt. Return a deterministic canned reply that echoes the
context (e.g. rating/action/summary if parseable) so offline dev works. Keep it simple.

### 5. Config

No new required settings - reuses `llm_provider`, rate limiter, and
`analysis_min_interval_seconds` guard. Optional: expose `chat_max_history` /
`chat_max_message_chars` as settings with defaults (no migration needed).

### 6. Tests: `backend/tests/test_chat.py`

- Auth required (401 without token).
- Holding chat: can't chat about another user's holding (404).
- Holding chat: 404 when no analysis exists for the holding.
- Portfolio chat: 404 when no analysis exists.
- Message validation (empty -> 422).
- Mock provider returns a reply; response shape includes `reply`, `provider`,
  `modelName`.
- History truncation / message length caps.

---

## Frontend

### 7. New component: `src/components/analysis/ask-ai.tsx` + `ask-ai.module.css`

Reusable chat panel. Props:

```ts
{ context: "portfolio" | "holding"; holdingId?: string; label?: string }
```

Features:

- Message list (user right / assistant left), input `textarea` (Enter to send,
  Shift+Enter newline), Send button, loading "thinking" indicator, inline error with
  retry, auto-scroll to latest.
- **Session-only history** in `useState` - matches decision #1. Sends the last ~10
  messages with each request.
- Suggested starter-question chips (context-aware), only shown when analysis exists:
  - portfolio: "Which positions need attention?", "How concentrated is my portfolio?",
    "What should I do first?"
  - holding: "Why this rating?", "What should I watch for?", "Should I add or reduce?"
- **Disabled/empty state (Option B):** if no analysis exists for the context, show the
  chat UI in a muted state with a message like "Run an analysis first to ask questions
  about this stock/portfolio." No suggested-question chips until analysis exists.
  Auto-enables once a new analysis completes (pages already reload via `handleComplete`).
- Renders replies as plain text with `white-space: pre-wrap` (no new markdown
  dependency). AI disclaimer line.

**Design (impeccable product register):** dashboard/tool surface, design serves the
product. Chat is a secondary supporting affordance - build as a **docked panel/card**
(not a full-screen takeover or floating FAB that hides the analysis), with:

- Calm, single accent color from the existing token system (reuse existing CSS
  variables; no new brand work - identity-preservation wins, app already has committed
  tokens in page module CSS).
- Clear visual hierarchy: user vs assistant bubbles distinguished by surface tint, not
  color overload; readable contrast (>= 4.5:1 body).
- Proper spacing rhythm, semantic z-index, `prefers-reduced-motion` respected for
  message entrance.
- Responsive: on mobile, chat becomes a full-width stacked section below the analysis;
  on desktop it sits as a side/full-width card. No side-stripe borders, no gradient
  text, no identical card grids.
- Accessible: labeled input, `aria-live` on assistant replies, focus management,
  visible focus states.

Verify responsive behavior at desktop and mobile widths per AGENTS.md after
implementation.

### 8. API + types

- `src/lib/api.ts`: add `api.askAi(input): Promise<{ reply; provider; modelName }>`
  -> `POST /analysis/chat`.
- `src/lib/types.ts`: add `ChatMessage`, `ChatRequest`, `ChatResponse` types.

### 9. Wire into pages

- `src/app/ai/page.tsx` - render `<AskAi context="portfolio" />` below the portfolio
  view. Disable (muted, "run analysis first") when analysis data is null.
- `src/app/holdings/[id]/page.tsx` - render
  `<AskAi context="holding" holdingId={holding.id} />` below the recommendation view.
  Disable when `rec` is null.

---

## Non-goals / notes

- No DB migration, no chat tables (session-only per decision #1).
- No streaming (per decision #2) - simple request/response.
- No live re-fetch of market data per question - answers come from stored analysis +
  holdings (per decision #3).
- No new frontend markdown dependency.

---

## Suggested implementation order

1. Backend: prompt file -> chat.py service -> mock provider chat branch -> schema ->
   endpoint -> tests.
2. Frontend: types -> api.ts -> AskAi component + CSS -> wire into both pages ->
   responsive verification.
3. Run backend `pytest tests -q` and frontend `npm run build` + `npm run lint`.
