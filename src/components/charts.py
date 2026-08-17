"""Shared Plotly chart-building functions reused across pages/sizes.

Per 03-UI-SPEC.md's "same rendering function reused ... not two
independently-built components" requirement, `build_breakdown_figure` and
`build_price_history_figure` are each a single, independently-testable
function reused at both compact (recommendation card) and larger
(drill-in/search) render sizes by `src/pages/recommendations.py` and
`src/pages/search.py` (Plans 06/07).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

CHART_MARK_COLOR = "#334155"
FORECAST_COLOR = "#0EA5E9"
CI_FILL_COLOR = "rgba(14, 165, 233, 0.2)"


def build_breakdown_figure(sub_scores_display: dict) -> go.Figure:
    """Return a horizontal bar chart of sub-factor scores.

    Preserves the input dict's iteration order (never re-sorted by value)
    so REC-02's fixed sub-factor display order (SUB_SCORE_ORDER from
    explain.py) is respected. Plotly renders the first ``y`` category at
    the bottom of a horizontal bar chart by default, so the y-axis is
    explicitly reversed to make the rendered chart read top-to-bottom in
    the same order as ``sub_scores_display``.
    """
    bar = go.Bar(
        x=list(sub_scores_display.values()),
        y=list(sub_scores_display.keys()),
        orientation="h",
        marker_color=CHART_MARK_COLOR,
    )
    fig = go.Figure(data=[bar])
    fig.update_yaxes(autorange="reversed")
    return fig


def render_breakdown_bar_chart(sub_scores_display: dict, key: str) -> None:
    """Render the sub-factor breakdown bar chart via st.plotly_chart."""
    st.plotly_chart(build_breakdown_figure(sub_scores_display), key=key)


def build_price_history_figure(price_df: pd.DataFrame) -> go.Figure:
    """Return a single-line historical price chart from a DataFrame with
    a "Close" column."""
    scatter = go.Scatter(
        x=price_df.index,
        y=price_df["Close"],
        mode="lines",
        line_color=CHART_MARK_COLOR,
    )
    return go.Figure(data=[scatter])


def render_price_history_chart(price_df: pd.DataFrame, key: str) -> None:
    """Render the historical price line chart via st.plotly_chart."""
    st.plotly_chart(build_price_history_figure(price_df), key=key)


def build_forecast_figure(
    price_df: pd.DataFrame, forecast_index, forecast_values, ci_lower, ci_upper
) -> go.Figure:
    """Return the historical price chart with a dashed forecast line and a
    shaded confidence-interval band overlaid on top (PRED-03).

    Reuses `build_price_history_figure` for the historical line rather than
    reimplementing it, then adds 3 more traces: an invisible CI-upper-bound
    line, an invisible CI-lower-bound line with `fill="tonexty"` (producing
    the shaded band between the two), and the visible dashed forecast line.
    Per 04-RESEARCH.md Pattern 6 (Plotly's standard `fill='tonexty'`
    continuous-error-band idiom).
    """
    fig = build_price_history_figure(price_df)
    fig.add_trace(
        go.Scatter(
            x=forecast_index,
            y=ci_upper,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast_index,
            y=ci_lower,
            mode="lines",
            fill="tonexty",
            fillcolor=CI_FILL_COLOR,
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast_index,
            y=forecast_values,
            mode="lines",
            line=dict(color=FORECAST_COLOR, dash="dash"),
        )
    )
    return fig


def render_forecast_chart(
    price_df: pd.DataFrame,
    forecast_index,
    forecast_values,
    ci_lower,
    ci_upper,
    key: str,
) -> None:
    """Render the forecast + CI band chart via st.plotly_chart."""
    st.plotly_chart(
        build_forecast_figure(
            price_df, forecast_index, forecast_values, ci_lower, ci_upper
        ),
        key=key,
    )
