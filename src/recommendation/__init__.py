"""Deterministic recommendation-engine package (Phase 3).

Every module in this package is pure and zero-I/O -- functions take
already-fetched data (a feature row, a universe DataFrame, a profile dict)
as input and return a computed value. This package never fetches its own
data and never imports ``streamlit``, ``yfinance``, or ``sqlite3``; it
imports only ``pandas``/``numpy`` and sibling ``recommendation.*`` modules,
matching ``src/features/``'s module-boundary discipline.

The recommendation engine has no Gemini/agent/network dependency: no
LLM/network call is ever used to compute a score. The shared fetch/assemble
I/O loop that feeds this package lives outside of it, in
``src/pages/_universe_loader.py``.
"""
