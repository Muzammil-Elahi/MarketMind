"""Shared pytest fixtures for Popcorn Pilot's test suite.

`supabase_env` shells out to `npx supabase status -o env` to discover the
running local Supabase CLI stack's connection details (API_URL, ANON_KEY,
DB_URL, INBUCKET_URL) and sets them into `os.environ` (SUPABASE_URL,
SUPABASE_ANON_KEY, SUPABASE_DB_URL, SUPABASE_INBUCKET_URL) before any test
imports `src.config`/`src.data.supabase_client` — so every test in this suite
exercises the real local Supabase stack, never a mock.
"""

import os
import re
import subprocess
from uuid import uuid4

import pytest

_ENV_LINE = re.compile(r'^([A-Z_][A-Z0-9_]*)="?(.*?)"?$')

# Fixed test password used by every user test_user_factory creates. Real
# accounts on a throwaway local Supabase stack — not a secret.
TEST_PASSWORD = "correct horse battery staple 1"


def _parse_supabase_status_env(output: str) -> dict:
    """Parse `npx supabase status -o env` KEY="VALUE" lines into a dict."""
    values = {}
    for line in output.splitlines():
        line = line.strip()
        match = _ENV_LINE.match(line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


@pytest.fixture(scope="session", autouse=True)
def supabase_env():
    """Point the test process at the running local Supabase CLI stack.

    Runs once per test session (autouse — every test needs this configured
    before it can import src.config/src.data.supabase_client).
    """
    result = subprocess.run(
        ["npx", "supabase", "status", "-o", "env"],
        capture_output=True,
        text=True,
        shell=(os.name == "nt"),
    )
    if result.returncode != 0:
        pytest.fail(
            "`npx supabase status -o env` failed — is the local Supabase CLI "
            f"stack running (npx supabase start)? stderr:\n{result.stderr}"
        )

    values = _parse_supabase_status_env(result.stdout)

    os.environ["SUPABASE_URL"] = values["API_URL"]
    os.environ["SUPABASE_ANON_KEY"] = values["ANON_KEY"]
    os.environ["SUPABASE_DB_URL"] = values["DB_URL"]
    os.environ["SUPABASE_INBUCKET_URL"] = values["INBUCKET_URL"]

    return values


@pytest.fixture
def test_user_factory(supabase_env):
    """Return a factory that signs up a fresh, uniquely-emailed real user.

    Each call creates a distinct real user against the local Supabase stack
    (no mocks) via `src.auth.session.sign_up`. Returns (email, password,
    sign_up_response) so callers can assert against the real AuthResponse.
    Used by this plan's tests and Plan 05's isolation tests, which need more
    than one distinct real user.
    """
    from src.auth import session as auth_session

    def _make_user():
        email = f"test-{uuid4().hex}@example.com"
        response = auth_session.sign_up(email, TEST_PASSWORD)
        return email, TEST_PASSWORD, response

    return _make_user
