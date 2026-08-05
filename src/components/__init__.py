"""Shared UI-layer components used across multiple Streamlit pages.

New package this phase introduces for UI elements shared across pages
(disclaimer banner, chart builders) -- explicitly not part of
`src/recommendation/` (which stays zero-I/O/zero-Streamlit) nor
page-specific, since both `src/pages/recommendations.py` and
`src/pages/search.py` (Plans 06/07) need identical copies of each.
"""
