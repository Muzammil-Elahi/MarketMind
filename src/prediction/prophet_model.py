"""Prophet forecast model, import-guarded (PRED-02/PRED-03).

Prophet natively produces a full daily forecast path with ``yhat``,
``yhat_lower``, ``yhat_upper`` columns via ``interval_width``. Because
Prophet's Stan backend (``cmdstanpy``) can fail independently of the Python
import machinery itself (a bad transitive CmdStan install on the deployed
Streamlit Community Cloud build environment -- 04-RESEARCH.md Pitfall 1), the
top-level Prophet class import below is wrapped in a broad ``except
Exception`` guard so a degraded install disables exactly this one model
option, never the whole ``src/prediction/`` package or the drill-in page
(04-RESEARCH.md Pattern 4).

``prophet_model.py`` is the *only* module in ``src/prediction/`` (or
elsewhere in this codebase) that imports the ``prophet`` package directly --
every other module that needs a Prophet forecast must import this module and
check ``PROPHET_AVAILABLE`` first, never import ``prophet`` itself.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except Exception:  # ImportError, or a cmdstanpy backend failure at import time
    logger.exception("Prophet import failed -- disabling the Prophet model option")
    PROPHET_AVAILABLE = False

INTERVAL_WIDTH = 0.80  # matches sma_model.py's Z_80PCT-implied 80% band


def forecast_forward(close: pd.Series, horizon_days: int) -> dict:
    """Fit Prophet on ``close`` and forecast ``horizon_days`` steps forward.

    Returns ``{"forecast": ndarray, "ci_lower": ndarray, "ci_upper":
    ndarray}``, each of length ``horizon_days``, sourced directly from
    Prophet's own ``yhat``/``yhat_lower``/``yhat_upper`` columns at
    ``interval_width=INTERVAL_WIDTH`` (PRED-03).

    Raises:
        RuntimeError: if ``PROPHET_AVAILABLE`` is ``False`` -- callers
            should catch this one specific, predictable failure mode rather
            than an unbound-symbol ``NameError``/``AttributeError``.
    """
    if not PROPHET_AVAILABLE:
        raise RuntimeError("Prophet is not available in this environment")

    df = pd.DataFrame({"ds": close.index, "y": close.values})
    model = Prophet(interval_width=INTERVAL_WIDTH)
    model.fit(df)
    future = model.make_future_dataframe(periods=horizon_days)
    forecast = model.predict(future).tail(horizon_days)

    return {
        "forecast": forecast["yhat"].to_numpy(),
        "ci_lower": forecast["yhat_lower"].to_numpy(),
        "ci_upper": forecast["yhat_upper"].to_numpy(),
    }
