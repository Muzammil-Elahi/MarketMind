---
status: testing
phase: 04-multi-model-prediction-walk-forward-backtesting
source: [04-VERIFICATION.md]
started: 2026-08-17T04:23:45Z
updated: 2026-08-17T04:23:45Z
---

## Current Test

number: 1
name: Streamlit Community Cloud Prophet deploy validation
expected: |
  Prophet imports/fits successfully on the actual Streamlit Cloud Debian build image within a
  reasonable time, matching the local dev-machine result recorded in 04-05-SUMMARY.md (which
  required manual CmdStan/RTools installation steps not present in a stock Cloud build).
awaiting: user response

## Tests

### 1. Streamlit Community Cloud Prophet deploy validation
expected: |
  Deploy to Streamlit Community Cloud (or otherwise confirm the deploy build environment) and
  check that the build log shows a `prophet` wheel install (not a CmdStan source compile step),
  then time the first Prophet forecast on the deployed app. Prophet should import/fit successfully
  on the actual Cloud Debian build image within a reasonable time.
result: [pending]

### 2. Compare All Models end-to-end interaction
expected: |
  Click "Compare All Models" on an asset with sufficient history (e.g. AAPL) and observe the
  interaction end-to-end. An @st.dialog modal opens with the time-cost warning; clicking "Start
  Comparison" closes the modal and a persistent yellow st.warning banner appears while all 3
  models train sequentially; a st.toast reading "Model comparison ready." fires exactly once when
  done; a 3-column result view appears in sma/xgboost/prophet order.
result: [pending]

### 3. Wide/narrow-viewport chart rendering
expected: |
  Generate a forecast for a high-volatility asset (e.g. a crypto ticker) at the 90-day horizon and
  visually inspect the resulting chart. The wide confidence-interval band should autoscale via
  Plotly's default y-axis behavior without visually distorting or compressing the historical-price
  portion of the same chart; the chart should remain readable at a narrow (mobile-width) browser
  viewport.
result: [pending]

### 4. Loading-state and message-copy text wrapping
expected: |
  Trigger the "Generate Forecast" button for each of the 3 models (SMA, XGBoost, Prophet) and
  observe the loading state; also trigger the insufficient-history and Prophet-unavailable message
  states and check text wrapping. SMA should feel instant, XGBoost should take a couple seconds,
  Prophet should take several seconds -- all shown via a native st.spinner with no jank or unstyled
  flash. INSUFFICIENT_HISTORY_MESSAGE and PROPHET_UNAVAILABLE_MESSAGE should wrap cleanly inside
  their st.warning boxes at normal and narrow viewport widths.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
