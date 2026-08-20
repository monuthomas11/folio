---
name: Folio
description: Sharp, focused portfolio dashboard for Indian share holdings
colors:
  market-pine: "oklch(0.43 0.085 170)"
  market-pine-deep: "oklch(0.37 0.09 170)"
  market-pine-ink: "oklch(0.31 0.09 170)"
  market-pine-tint: "oklch(0.93 0.028 170)"
  market-pine-ink-on-tint: "oklch(0.32 0.07 170)"
  ember-accent: "oklch(0.62 0.12 50)"
  ember-tint: "oklch(0.94 0.04 65)"
  gain-green: "oklch(0.45 0.13 152)"
  gain-fill: "oklch(0.948 0.032 152)"
  loss-red: "oklch(0.46 0.17 27)"
  loss-fill: "oklch(0.948 0.034 27)"
  warn-amber: "oklch(0.5 0.1 75)"
  warn-fill: "oklch(0.945 0.034 78)"
  paper: "oklch(0.992 0.003 175)"
  page: "oklch(0.976 0.005 175)"
  sidebar: "oklch(0.972 0.006 170)"
  paper-tinted: "oklch(0.955 0.008 170)"
  paper-tinted-2: "oklch(0.94 0.012 170)"
  hairline: "oklch(0.925 0.008 172)"
  hairline-strong: "oklch(0.86 0.01 172)"
  ink: "oklch(0.22 0.02 170)"
  ink-strong: "oklch(0.15 0.018 170)"
  muted: "oklch(0.46 0.016 170)"
  faint: "oklch(0.61 0.013 170)"
  placeholder: "oklch(0.5 0.014 170)"
typography:
  display:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1.875rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    letterSpacing: "0.05em"
    textTransform: "uppercase"
rounded:
  sm: "0.375rem"
  md: "0.5rem"
  lg: "0.75rem"
  xl: "1rem"
  full: "9999px"
spacing:
  space-1: "0.25rem"
  space-2: "0.5rem"
  space-3: "0.75rem"
  space-4: "1rem"
  space-5: "1.25rem"
  space-6: "1.5rem"
  space-8: "2rem"
  space-10: "2.5rem"
  space-12: "3rem"
  space-16: "4rem"
  space-20: "5rem"
components:
  button-primary:
    backgroundColor: "{colors.market-pine}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "0 1.25rem"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.market-pine-deep}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "0 1.25rem"
    height: "40px"
  button-primary-active:
    backgroundColor: "{colors.market-pine-ink}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "0 1.25rem"
    height: "40px"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 1.25rem"
    height: "40px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
    padding: "0 1.25rem"
    height: "40px"
  input-text:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "40px"
    padding: "0 0.75rem"
  status-pill:
    backgroundColor: "{colors.paper-tinted-2}"
    textColor: "{colors.muted}"
    rounded: "{rounded.full}"
    height: "24px"
    padding: "0 10px"
  nav-item:
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
    height: "40px"
    padding: "0 0.75rem"
  nav-item-active:
    backgroundColor: "{colors.market-pine-tint}"
    textColor: "oklch(0.32 0.07 170)"
    rounded: "{rounded.md}"
    height: "40px"
    padding: "0 0.75rem"
  kpi-card:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.lg}"
    padding: "1.25rem 1.5rem"
---

# Design System: Folio

## 1. Overview

**Creative North Star: "The Investor's Ledger"**

Folio is a ledger the investor can trust at a glance. Every screen reads like a well-kept trading journal: calm, precise, and unhurried. The personality is sharp and analytical — nothing decorative, nothing urgent, nothing theatrical. The interface earns its density through real information: prices, quantities, P/L, stop-losses, and targets, all rendered in tabular numerals so a column of numbers can be compared by eye.

The palette is near-white paper tinted ever so slightly toward the primary's own green-teal hue, with a single deep Market Pine voice for actions and active states. Depth comes from tonal layering and hairline borders first; shadows appear only where a surface genuinely lifts (cards, the drawer, the brand mark). Color never carries meaning alone — gain and loss always pair with a label or direction arrow — because the investor may be color-blind, and the ledger must still be legible.

This system explicitly rejects the trading terminal (no dark screens, no glowing charts, no flickering tickers) and the generic SaaS cliché (no gradient text, no glassmorphism, no hero-metric landing, no identical icon-card grids). Folio's calm is a feature: the market is loud, the dashboard is not.

**Key Characteristics:**
- One accent voice (Market Pine) for action and active state; semantic greens/reds/ambers only for P/L state.
- Hairline borders and tonal surfaces over shadows; elevation is quiet and earned.
- Tabular numerals everywhere numbers align in a column.
- A single type family (Geist) carrying the whole hierarchy — contrast through weight, not font pairing.
- Sticky, conventional structure (fixed sidebar, page headers, panel grid) so the data, not the chrome, gets the attention.

## 2. Colors

A neutral palette tinted toward the primary's green-teal hue (OKLCH hue 170), carrying one deep teal-green action color and a disciplined set of semantic P/L colors. No warm beige, no navy, no gradient.

### Primary
- **Market Pine** (`oklch(0.43 0.085 170)`): the single voice of action and identity — primary buttons, active nav item, brand mark, focus rings, gain-position accent. On the tinted surfaces it reads as confident teal-green without shouting.
- **Market Pine Deep** (`oklch(0.37 0.09 170)`): hover state of primary actions.
- **Market Pine Ink** (`oklch(0.32 0.09 170)`): pressed state of primary actions.
- **Market Pine Tint** (`oklch(0.936 0.024 170)`): the 2% confidence wash behind active nav, avatars, pills, and text selection. Text on tint must use a darker pine like `oklch(0.38 0.07 170)`, never the bare ink gray.

### Secondary
- **Ember Accent** (`oklch(0.62 0.12 50)`): a warm amber reserved for the AI Advisor surface and one-off highlights. It is the only warm hue in the system; use it like a rare spice, never as a default.

### Tertiary
- **Gain Green** (`oklch(0.47 0.13 152)`) with **Gain Fill** (`oklch(0.952 0.03 152)`): positive P/L, "in profit" breadth, healthy status.
- **Loss Red** (`oklch(0.47 0.17 27)`) with **Loss Fill** (`oklch(0.952 0.032 27)`): negative P/L, at-stop-loss status, error banners. Never pure `#f00`; this is a muted, mature red.
- **Warn Amber** (`oklch(0.5 0.1 75)`) with **Warn Fill** (`oklch(0.948 0.032 78)`): near-target / caution state and the market-status dot.

### Neutral
- **Paper** (`oklch(0.992 0.003 175)`): the card, table, and panel surface — near-white with a whisper of the brand hue. All lifted surfaces sit on Paper.
- **Page** (`oklch(0.976 0.005 175)`) and **Sidebar** (`oklch(0.972 0.006 170)`): the page background and the nav rail. The page is never pure white; cards lift off it by tone, not shadow.
- **Tinted Paper** (`oklch(0.955 0.008 170)`) and **Tinted Paper 2** (`oklch(0.94 0.012 170)`): table header bands, hover fills, quiet chips, skeletons. The green-teal hue at near-zero chroma keeps neutrals cool-green, never warm.
- **Hairline** (`oklch(0.924 0.007 170)`) and **Hairline Strong** (`oklch(0.86 0.009 170)`): borders and separators; the strong variant edges inputs and secondary buttons.
- **Ink** (`oklch(0.22 0.02 170)`) and **Ink Strong** (`oklch(0.16 0.018 170)`): body and emphasized text. Ink Strong is the headline color.
- **Muted** (`oklch(0.46 0.016 170)`): secondary text, nav labels, card labels. **Faint** (`oklch(0.62 0.012 170)`): tertiary text, icons at rest, the market dot. **Placeholder** (`oklch(0.5 0.014 170)`): form placeholder — deliberately darker than Faint so placeholder text stays legible (≥4.5:1).

### Named Rules
**The One-Voice Rule.** Market Pine is the only action color. One primary action per view; secondary and ghost exist so a screen never holds two pine buttons competing.

**The No-Gray-Gain Rule.** Gain and loss are never expressed as gray or as contrast alone. Always pair the semantic color with a label, a direction arrow, or a dot — color is an enhancement, not the message.

**The Tinted-Paper Rule.** Every near-white neutral is tinted toward hue 170–175 (the brand's own hue) with chroma 0.003–0.012. Warm beige, cream, and sand are prohibited as backgrounds.

## 3. Typography

**Display Font:** Geist Sans (variable, weights 100–900), fallback `ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif`.
**Label/Mono Font:** Geist Mono (variable), reserved for symbol-level meta and code-adjacent detail.
**Character:** One family, one voice. Hierarchy comes from weight, size, and letter-spacing — never from a second font. Numbers are the product's content, so tabular alignment is non-negotiable.

### Hierarchy
- **Display** (700, 1.875rem / 30px, line-height 1.15, tracking -0.02em): page titles ("Dashboard", "Portfolio"). One per page.
- **Headline** (700, 1.5rem / 24px, line-height 1.15, tracking -0.02em): KPI values, panel header values. The largest *number* size — big enough to scan across the KPI row.
- **Title** (700, 1.125rem / 18px, line-height 1.2, tracking -0.01em): panel titles, section headings, the brand name.
- **Body** (400, 0.875rem / 14px, line-height 1.5): default UI text, table cells, descriptions. Prose capped at 65–75ch.
- **Label** (600, 0.6875rem / 11px, uppercase, tracking 0.05–0.08em): field labels, KPI labels, overlines. The tiny-uppercase treatment is deliberate here — it's the *only* scale in the system, applied consistently to every label, so it reads as a voice rather than a kicker.

### Named Rules
**The Tabular Numbers Rule.** Every price, quantity, and percentage uses `font-variant-numeric: tabular-nums`. A column of P/L must align like a printed statement.

**The Label-Uppercase Rule.** Labels are always 11px, 600, uppercase, tracking 0.05–0.08em — never bold body text wearing a caps class, never 12–13px "small caps" hybrids.

**The Uppercase-Ceiling Rule.** Uppercase is for labels only. Never uppercase a heading, a button label, or prose.

## 4. Elevation

Quiet lift. Surfaces are flat at rest; the system's primary depth signal is tonal layering (Paper → Tinted Paper → Tinted Paper 2) plus hairline borders. Shadows are a second-class citizen, used only where a surface genuinely detaches from the page: resting cards, the brand mark, the loader, and (at the high step) overlays and the drawer.

### Shadow Vocabulary
- **Ambient Low** (`0 1px 2px oklch(0.2 0.02 170 / 0.05)`): resting cards, buttons, the brand mark. Barely-there.
- **Ambient Mid** (`0 4px 14px -2px oklch(0.2 0.02 170 / 0.08)`): the loader mark and small lifted elements.
- **Ambient High** (`0 16px 40px -12px oklch(0.2 0.02 170 / 0.16)`): drawer, popovers, overlays. Depth for floating surfaces only.

### Named Rules
**The Quiet-Lift Rule.** Elevation through tone first, shadow second. If a surface sits on the page background, it needs a hairline border or a tint, not a shadow. No element may use more than one shadow step.

## 5. Components

### Buttons
- **Shape:** Gently rounded (0.5rem / 8px radius), 40px height (md) or 34px (sm), 600 weight at 13px (11px for sm).
- **Primary:** Market Pine fill, white text, Ambient Low shadow. Hover → Market Pine Deep; pressed → Market Pine Ink; pressed also nudges down 1px.
- **Secondary:** Paper fill, Ink text, Hairline Strong border. Hover → Tinted Paper fill with the border deepening to Ink.
- **Ghost:** Transparent, Muted text. Hover → Tinted Paper fill, Ink text.
- **States:** Disabled = 55% opacity with `not-allowed` cursor; focus = 2px Market Pine ring with 2px offset. Transitions are fast (120ms) with ease-out-expo; active states use transform, never layout.

### Status Pills
- **Shape:** 24px tall capsules (full radius), 11px/600 text, a 6px leading status dot.
- **Healthy:** Market Pine Tint fill, dark pine text, pine dot. **Warn:** Warn Fill, dark amber text. **Danger:** Loss Fill, dark red text. **Gain:** Gain Fill. **Neutral:** Tinted Paper 2, Muted text, Faint dot.
- **Role:** State-at-a-glance chips for position status. The dot plus the fill plus the label triples redundancy — a single channel can fail and the state still reads.

### Cards / Containers
- **Corner Style:** Rounded 0.75rem (12px), KPI cards 12px; the add-holding form and login card use 16px.
- **Background:** Paper, hairline border, Ambient Low shadow.
- **Internal Padding:** 1.25rem × 1.5rem on KPI cards (1rem × 1.25rem on mobile); panels follow the same rhythm. Nested cards are prohibited — a card is a leaf, not a container.

### Inputs / Fields
- **Style:** 40px height, 1px Hairline Strong border, 8px radius, Paper fill, 13px text, 0.75rem padding.
- **Focus:** border and label shift to Market Pine; focus-visible ring is 2px Market Pine at 2px offset. Focus always visible.
- **Placeholder:** Placeholder token (`oklch(0.5 0.014 170)`) — legible at ≥4.5:1, never the default faint gray.
- **Error:** red-tinted surface with a loss-red border, message in Loss Red.

### Navigation
- **Sidebar:** Fixed 248px rail on the Sidebar surface, hairline right border. Nav items are 40px rows, 8px radius, Muted text with Faint icons; hover → Tinted Paper; active → Market Pine Tint with dark-pine text and a pine icon. The alert badge is a Market Pine capsule with white count.
- **Topbar:** Sticky, 60px, Paper at 85% with a soft backdrop blur, hairline bottom border; collapses to a menu-drawer under 760px.
- **Drawer:** 288px, slides in with ease-out-expo (320ms), dims the page with Ink at 40%, Ambient High shadow.

### Brand Mark
A 32px Market Pine rounded square carrying the 16px grid icon in white, with an Ambient Low shadow; 44px and a pulse in the loading state.

## 6. Do's and Don'ts

### Do:
- **Do** keep the Market Pine voice exclusive: one primary action per view, secondary/ghost everywhere else.
- **Do** use tabular numerals for every price, quantity, P/L, and percentage.
- **Do** prefer tonal layering and hairline borders for depth; reach for shadows only when a surface really lifts.
- **Do** pair gain/loss color with a label, arrow, or dot — never color alone.
- **Do** respect reduced motion: transitions collapse to near-instant, pulses stop.
- **Do** keep placeholder text at ≥4.5:1 contrast; never the muted-gray default.
- **Do** use the 11px uppercase label style consistently for field and KPI labels — it's the system's voice, not an eyebrow.

### Don't:
- **Don't** build a trading terminal: no dark backgrounds, no glowing or flickering charts, no blinking tickers, no urgency theatrics.
- **Don't** reach for SaaS clichés: no gradient text, no glassmorphism, no hero-metric landing hero, no identical icon-card grids, no "01 / 02 / 03" scaffolding.
- **Don't** use warm beige, cream, or sand backgrounds; every neutral tints toward hue 170.
- **Don't** use a colored `border-left` or `border-right` accent stripe on cards, list items, or alerts — use full borders, tints, or dots.
- **Don't** nest cards. A card is a leaf.
- **Don't** use gray or pure `#f00` for gain/loss; the semantic red is a muted `oklch(0.47 0.17 27)`.
- **Don't** uppercase headings, buttons, or prose — uppercase is the label style only.
- **Don't** use arbitrary z-index values (999/9999); the token scale is dropdown → sticky → backdrop → modal → toast → tooltip.