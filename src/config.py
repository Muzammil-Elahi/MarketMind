"""Shared configuration access for Popcorn Pilot.

Resolution order for any config key:
1. ``st.secrets`` — populated on Streamlit Community Cloud (or locally via
   ``.streamlit/secrets.toml``). Reading ``st.secrets`` raises when no
   secrets file exists at all (e.g. plain local/CI runs), so that failure
   mode is treated as "not found" rather than a hard error.
2. ``os.environ`` — populated locally via a ``.env`` file (loaded below) or
   the shell/CI environment.
"""

import os

import dotenv

# Load a local .env file if present. No-op (returns False) when no .env
# file exists, so this is always safe to call at import time.
dotenv.load_dotenv()

# Live price data cache TTL in seconds (D-08): 1 hour. Imported by
# data/cache.py's st.cache_data(ttl=CACHE_TTL_SECONDS) decorator.
CACHE_TTL_SECONDS = 3600


def get_config(key: str, default: str | None = None) -> str | None:
    """Resolve a config value by key.

    Tries st.secrets first, then falls back to environment variables
    (including any loaded from a local .env file).
    """
    try:
        import streamlit as st

        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # st.secrets raises when no secrets.toml exists (e.g. outside
        # Streamlit Cloud with no local secrets file) or when not running
        # inside a Streamlit context at all — treat as "not found".
        pass

    return os.environ.get(key, default)
