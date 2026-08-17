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
    CI_FILL_COLOR,
    FORECAST_COLOR,
    build_breakdown_figure,
    build_forecast_figure,
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


def test_forecast_color_and_ci_fill_color_match_ui_spec_exactly():
    assert FORECAST_COLOR == "#0EA5E9"
    assert CI_FILL_COLOR == "rgba(14, 165, 233, 0.2)"


def _forecast_fixture():
    price_df = pd.DataFrame({"Close": [100.0, 101.5, 99.0, 102.25]})
    forecast_index = [4, 5, 6]
    forecast_values = [103.0, 104.0, 105.0]
    ci_lower = [101.0, 101.5, 102.0]
    ci_upper = [105.0, 106.5, 108.0]
    return price_df, forecast_index, forecast_values, ci_lower, ci_upper


def test_build_forecast_figure_returns_four_traces_in_order():
    price_df, forecast_index, forecast_values, ci_lower, ci_upper = (
        _forecast_fixture()
    )

    figure = build_forecast_figure(
        price_df, forecast_index, forecast_values, ci_lower, ci_upper
    )

    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 4

    historical, ci_upper_trace, ci_lower_trace, forecast_trace = figure.data

    # Trace [0]: historical line, byte-identical to build_price_history_figure
    expected_historical = build_price_history_figure(price_df).data[0]
    assert list(historical.x) == list(expected_historical.x)
    assert list(historical.y) == list(expected_historical.y)

    # Trace [1]: invisible CI-upper-bound line
    assert list(ci_upper_trace.x) == list(forecast_index)
    assert list(ci_upper_trace.y) == list(ci_upper)
    assert ci_upper_trace.line.width == 0
    assert ci_upper_trace.showlegend is False
    assert ci_upper_trace.hoverinfo == "skip"

    # Trace [2]: invisible CI-lower-bound line with fill="tonexty"
    assert list(ci_lower_trace.x) == list(forecast_index)
    assert list(ci_lower_trace.y) == list(ci_lower)
    assert ci_lower_trace.fill == "tonexty"
    assert ci_lower_trace.fillcolor == CI_FILL_COLOR
    assert ci_lower_trace.line.width == 0
    assert ci_lower_trace.showlegend is False
    assert ci_lower_trace.hoverinfo == "skip"

    # Trace [3]: visible dashed forecast line
    assert list(forecast_trace.x) == list(forecast_index)
    assert list(forecast_trace.y) == list(forecast_values)
    assert forecast_trace.line.color == FORECAST_COLOR
    assert forecast_trace.line.dash == "dash"


def test_build_forecast_figure_uses_forecast_and_ci_fill_colors():
    price_df, forecast_index, forecast_values, ci_lower, ci_upper = (
        _forecast_fixture()
    )

    figure = build_forecast_figure(
        price_df, forecast_index, forecast_values, ci_lower, ci_upper
    )

    _, _, ci_lower_trace, forecast_trace = figure.data
    assert forecast_trace.line.color == FORECAST_COLOR
    assert ci_lower_trace.fillcolor == CI_FILL_COLOR


def test_build_forecast_figure_preserves_ci_lower_forecast_ci_upper_ordering():
    price_df, forecast_index, forecast_values, ci_lower, ci_upper = (
        _forecast_fixture()
    )
    assert all(
        ci_lower[i] <= forecast_values[i] <= ci_upper[i]
        for i in range(len(forecast_index))
    )

    figure = build_forecast_figure(
        price_df, forecast_index, forecast_values, ci_lower, ci_upper
    )

    _, ci_upper_trace, ci_lower_trace, forecast_trace = figure.data
    assert list(ci_lower_trace.y) == list(ci_lower)
    assert list(forecast_trace.y) == list(forecast_values)
    assert list(ci_upper_trace.y) == list(ci_upper)
    assert all(
        ci_lower_trace.y[i] <= forecast_trace.y[i] <= ci_upper_trace.y[i]
        for i in range(len(forecast_index))
    )
