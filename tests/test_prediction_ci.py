"""Cross-model CI-band invariant integration test (PRED-03), run through
the real end-to-end ``generate_forecast`` call path -- not each model's
own isolated unit test -- so a future change to any one model's
``forecast_forward`` that breaks the invariant is caught here even if
that model's own unit test is accidentally weakened.

No mocking anywhere in this file -- a fully real, small, fast fixture
proves the actual composed math works for all 3 models. Prophet's real
fit is the slowest part of this suite (mirrors
tests/test_prediction_prophet.py's note); it is skipped, not failed, if
``prophet_model.PROPHET_AVAILABLE`` is ``False`` in this environment
(matching engine.py's own Prophet-unavailable degrade-gracefully
contract, never a hard test failure for a genuinely absent optional
dependency).
"""

import pytest

from src.prediction import prophet_model
from src.prediction.engine import generate_forecast

# Bare top-level import -- see tests/test_prediction_backtest.py's comment
# on the globally installed unrelated `tests` PyPI package shadowing
# `tests.<module>` dotted imports in this environment.
from _prediction_fixtures import sample_feature_frame_and_price_series

TICKER = "AAPL"
HORIZON_DAYS = 7

# sma/xgboost compute their CI band width via a deterministic closed-form
# sqrt(time) scaling formula (04-RESEARCH.md A-07/Pattern 3 Design Note),
# so their day-7 band is guaranteed >= their day-1 band with zero
# tolerance. Prophet's band instead comes from the real `prophet` package's
# own finite-sample (uncertainty_samples=1000 by default) Monte Carlo
# quantile estimate of future trend uncertainty -- over a short 7-day
# horizon on a low-volatility fixture, the *true* expected width growth is
# small enough that MC sampling noise (empirically +/-~10% relative,
# unseeded, measured across 30 real fits against this exact fixture) can
# occasionally make day 1's *sampled* width exceed day 7's, even though
# Prophet's model is working correctly. A 20% relative tolerance absorbs
# that legitimate estimation noise while still catching a genuine
# composition bug (e.g. a collapsed/inverted band).
PROPHET_MC_NOISE_TOLERANCE = 0.20


@pytest.mark.parametrize("model", ["sma", "xgboost", "prophet"])
def test_generate_forecast_ci_band_invariant_holds_end_to_end(model):
    if model == "prophet" and not prophet_model.PROPHET_AVAILABLE:
        pytest.skip("Prophet not available in this environment")

    feature_frame, price_series = sample_feature_frame_and_price_series()

    result = generate_forecast(
        TICKER, model, HORIZON_DAYS, feature_frame, price_series, "Stocks"
    )

    assert result["status"] == "ok"
    forecast = result["forecast"]
    ci_lower = result["ci_lower"]
    ci_upper = result["ci_upper"]

    for i in range(HORIZON_DAYS):
        assert ci_lower[i] <= forecast[i] <= ci_upper[i]

    band_width = ci_upper - ci_lower
    if model == "prophet":
        assert band_width[-1] >= band_width[0] * (1 - PROPHET_MC_NOISE_TOLERANCE)
    else:
        assert band_width[-1] >= band_width[0]
