"""Tests for src/components/disclaimer.py and src/components/charts.py.

Covers the pure/figure-building functions and constants only (not the
`st.plotly_chart`/`st.container`-calling wrappers, which require a
running Streamlit script context to test meaningfully and are exercised
instead by Plans 06/07's human-check).
"""

import pandas as pd
import plotly.graph_objects as go

from src.components.charts import (
    CHART_MARK_COLOR,
    build_breakdown_figure,
    build_price_history_figure,
)
from src.components.disclaimer import DISCLAIMER_TEXT


def test_disclaimer_text_matches_ui_spec_copywriting_contract_exactly():
    assert DISCLAIMER_TEXT == (
        "For informational and educational purposes only — not financial "
        "advice. Scores and rankings are not personalized recommendations, "
        "and past performance does not predict future results."
    )


def test_chart_mark_color_matches_ui_spec_exactly():
    assert CHART_MARK_COLOR == "#334155"


def test_build_breakdown_figure_returns_figure_with_five_bars_in_input_order():
    sub_scores_display = {
        "profile_fit": 62,
        "momentum": 71,
        "volatility": 55,
        "quality": 48,
        "similarity": 67,
    }

    figure = build_breakdown_figure(sub_scores_display)

    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 1
    bar = figure.data[0]
    assert list(bar.y) == list(sub_scores_display.keys())
    assert list(bar.x) == list(sub_scores_display.values())


def test_build_breakdown_figure_bars_use_chart_mark_color():
    sub_scores_display = {
        "profile_fit": 62,
        "momentum": 71,
        "volatility": 55,
        "quality": 48,
        "similarity": 67,
    }

    figure = build_breakdown_figure(sub_scores_display)

    bar = figure.data[0]
    assert bar.marker.color == CHART_MARK_COLOR


def test_build_price_history_figure_returns_single_line_trace_matching_close():
    price_df = pd.DataFrame({"Close": [100.0, 101.5, 99.0, 102.25]})

    figure = build_price_history_figure(price_df)

    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 1
    scatter = figure.data[0]
    assert list(scatter.y) == price_df["Close"].tolist()
    assert scatter.line.color == CHART_MARK_COLOR
