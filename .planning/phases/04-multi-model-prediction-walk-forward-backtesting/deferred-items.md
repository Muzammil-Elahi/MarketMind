# Deferred Items — Phase 04

Items discovered during execution that are out of scope for the current
plan (pre-existing, not caused by this plan's changes) and are logged here
rather than auto-fixed, per the executor's scope-boundary rule.

## 04-02: pytest suite requires local Supabase Docker stack (environment gap, not a code issue)

- **Found during:** Plan 04-02, Task 1 verification step.
- **Issue:** `tests/conftest.py`'s `supabase_env` fixture is `scope="session", autouse=True` and shells out to `npx supabase status -o env`, which requires a running local Supabase CLI Docker stack. This fixture fires for every test session regardless of which test file is targeted (even `tests/test_components.py`, which has zero Supabase dependency), because `autouse=True` applies it to the whole session.
- **In this sandboxed worktree**, Docker Desktop's daemon is not reachable (`docker ps` fails with `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`), so `pytest tests/test_components.py -x -q` fails at fixture setup before any test in the file runs — independent of whether the file's own tests would pass.
- **Not fixed:** this is a pre-existing project-wide test-infrastructure decision (see PROJECT.md Key Decisions: "Automated tests for Phase 1 run against a local Supabase CLI Docker stack, not mocks or a live cloud project"), unrelated to `src/components/charts.py`/`tests/test_components.py`'s content, and out of this plan's scope to change.
- **Workaround used for this plan's verification:** manually imported and exercised `build_forecast_figure` directly via `python -c "..."` (bypasses `conftest.py` since `src.components.charts` has no Supabase import chain) to confirm all `<behavior>`/acceptance-criteria assertions hold. All checks passed. The equivalent assertions are also encoded as real pytest tests in `tests/test_components.py` and will pass once run in an environment with the local Supabase Docker stack running.
- **Recommendation:** if this environment gap recurs across other Phase 4 worktree plans, consider scoping `supabase_env` to only the test modules that actually need it (e.g. via a marker or by moving the fixture out of the root `conftest.py` into a package-level `conftest.py` under a `tests/integration/` or `tests/auth/` subdirectory) — but that is a cross-cutting test-infra change outside any single plan's `files_modified`, so it is deferred rather than made unilaterally here.
