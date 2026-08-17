"""Multi-model prediction + walk-forward backtesting package (Phase 4).

Every module in this package is pure and zero-I/O -- functions take
already-fetched data (a price/feature DataFrame, a fitted model, a set of
walk-forward fold boundaries) as input and return a computed value. This
package never fetches its own data and never imports ``streamlit``,
``yfinance``, or ``sqlite3``; it imports only ``pandas``/``numpy``,
``xgboost``, ``prophet`` (import-guarded, since a bad transitive CmdStan
install must degrade gracefully rather than crash the whole page), and
``sklearn`` (notably ``sklearn.model_selection.TimeSeriesSplit`` for
walk-forward fold generation), plus sibling ``prediction.*`` modules --
matching ``src/recommendation/``'s and ``src/features/``'s module-boundary
discipline.

The prediction/backtesting layer has no Gemini/agent/network dependency: no
LLM/network call is ever used to fit a model or compute a forecast. The
shared fetch/assemble I/O loop that feeds this package lives outside of it,
in ``src/pages/``.
"""
