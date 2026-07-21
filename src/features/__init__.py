"""Point-in-time feature engineering package.

Zero Streamlit and zero I/O imports live in this package -- every function
here takes an already-fetched OHLCV ``DataFrame`` (e.g. from
``src.data.prices.fetch_ohlcv``) as input and returns a computed
``Series``/``DataFrame``. This package never fetches its own data, matching
``src/data/prices.py``'s module-boundary discipline: callers are
responsible for obtaining the input DataFrame themselves.

``assemble_feature_frame`` (see ``feature_frame.py``) is the single shared
entry point Phase 3 (recommendation engine) and Phase 4
(prediction/backtesting) import later -- no duplicated feature-computation
logic should exist anywhere else in the codebase.
"""

from src.features.feature_frame import assemble_feature_frame

__all__ = ["assemble_feature_frame"]
