# Phase 4: Multi-Model Prediction + Walk-Forward Backtesting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-09
**Phase:** 4-Multi-Model Prediction + Walk-Forward Backtesting
**Areas discussed:** Model selection UX, Horizon & generation trigger, Backtest accuracy display, Insufficient-data handling

---

## Model selection UX

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown, one model at a time | Select a model from a dropdown, see its forecast + CI + backtest metrics. Simplest to build. | ✓ |
| Tabs, one model at a time | Same as dropdown but tab-styled navigation. | |
| Side-by-side comparison | All 3 models shown at once for direct comparison. Triples compute/training cost per load. | |

**User's choice:** Dropdown, one model at a time

| Option | Description | Selected |
|--------|-------------|----------|
| SMA baseline | Fastest to compute (no training), page loads with something immediately. | |
| XGBoost | The more "serious" default, but requires training on page load unless cached. | |
| No default — user must pick | Page shows price history chart only until user selects a model. | ✓ |

**User's choice:** No default — user must pick

---

## Horizon & generation trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed presets: 7 / 30 / 90 days | Small select of common horizons, simpler CI-width reasoning. | ✓ |
| Free slider (1-180 days) | Maximum flexibility, but very wide CIs at long horizons. | |
| Single fixed horizon | Simplest v1, no horizon UI at all. | |

**User's choice:** Fixed presets: 7 / 30 / 90 days

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit "Generate Forecast" button | Avoids surprising multi-second training delay on every dropdown change. | ✓ |
| Automatic on model/horizon change | More fluid, but Prophet's cmdstanpy cold-start could feel like a freeze. | |

**User's choice:** Explicit "Generate Forecast" button

---

## Backtest accuracy display

| Option | Description | Selected |
|--------|-------------|----------|
| Metrics table below the chart | Mirrors Phase 3's Score Breakdown pattern. | ✓ |
| Inline metric cards | More visual, more layout work. | |
| Compact one-liner | Minimal but least scannable. | |

**User's choice:** Metrics table below the chart

| Option | Description | Selected |
|--------|-------------|----------|
| Selected model only | Consistent with one-model-at-a-time dropdown UX, no comparison view to build. | (base) |
| Add a small all-models comparison table | Always-visible mini-table for all 3 models, requires backtesting all 3 up front. | |

**User's choice:** Hybrid, via freeform follow-up — selected model only by default, PLUS a separate "Compare all models" action. User specified: a popup/modal on selecting that action AND a persistent yellow warning banner on the page (both, not either/or), stating the comparison may take time since it may require training untrained models — plus a completion notification (toast/success) when the comparison finishes.
**Notes:** User explicitly rejected an either/or framing for the warning — wanted both the modal and the persistent banner. Exact notification widget left to Claude's discretion (Streamlit has no true push notifications).

---

## Insufficient-data handling

| Option | Description | Selected |
|--------|-------------|----------|
| Stricter, separate threshold | Own minimum-history constant, higher than Phase 3's MIN_HISTORY_ROWS, enough for several walk-forward folds. | ✓ |
| Reuse Phase 3's existing threshold | Simpler, but risks unreliable backtest metrics on barely-enough data. | |

**User's choice:** Stricter, separate threshold

| Option | Description | Selected |
|--------|-------------|----------|
| Chart renders, model/forecast UI disabled with a message | Matches Phase 3's D-08 precedent of never blocking the chart. | ✓ |
| Hide prediction section entirely | No explanation of why prediction isn't available. | |

**User's choice:** Chart renders, model/forecast UI disabled with a message

---

## Claude's Discretion

- Exact minimum-history threshold value for the stricter prediction/backtest floor, and the walk-forward fold/window scheme it must support.
- Exact widget/mechanism for the "Compare all models" completion notification.
- Whether prediction code lives in a new `src/prediction/` package (implied by existing `src/recommendation/` architecture, not explicitly discussed).

## Deferred Ideas

None raised during this discussion session. (Two related enhancement ideas — richer scoring explanation and portfolio-aware recommendations — were captured separately as backlog Phase 999.1 during the prior Phase 3 UAT conversation, not during this session.)
