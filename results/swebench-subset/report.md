# SWE-bench Subset — Docker Sandbox Run

Real bug-fix tasks constructed from well-known upstream Python repos (not
fabricated): each task checks out the buggy `base_commit`, adds the regression
test (`test_patch`), and is verified double-directionally before being run
through the agent in the Docker sandbox.

- **Model:** `deepseek-chat` (DeepSeek V3, via `.env` `DEEPSEEK_API_KEY`)
- **Sandbox:** `minicodex-swebench:latest` (`python:3.11-slim` + `pytest`)
- **Date:** 2026-09-02

## Results

| instance_id | repo | base_commit | result | exit | tool calls | cost |
|---|---|---|---|---|---|---|
| markupsafe__markupsafe-467 | pallets/markupsafe | b5291646 | PASS | finished | 6 | $0.056 |
| click__click-3677 | pallets/click | 7925a341 | PASS | LimitsExceeded | 25 | $1.078 |

**2/2 passed.** Both FAIL_TO_PASS / PASS_TO_PASS matrices were satisfied.

## Task details

### markupsafe__markupsafe-467
- **Bug:** `escape()` used `s.__class__ is str` to detect plain strings, which
  breaks for a proxy object that reports the proxied value's `__class__`.
- **Fix (gold):** `if type(s) is str:`.
- **FAIL_TO_PASS:** `tests/test_escape.py::test_proxy[markupsafe._native]`
- **PASS_TO_PASS:** `tests/test_markupsafe.py::test_adding[markupsafe._native]`,
  `tests/test_markupsafe.py::test_type_behavior[markupsafe._native]`
- **Agent produced the exact one-line fix** in 6 tool calls.

### click__click-3677
- **Bug:** `style()`/`secho()` dropped the 256-color index `0` (black) via a
  truthiness check and did not validate color arguments.
- **Fix (gold):** rewrite `_interpret_color` to honour index `0` and raise
  `ValueError` for invalid colors; `if fg is not None` instead of `if fg`.
- **FAIL_TO_PASS:** `tests/test_utils/test_style.py::test_styling_invalid_color`
- **PASS_TO_PASS:** `tests/test_utils/test_style.py::test_unstyle_other_ansi`
- The agent rewrote `_interpret_color` correctly; the run hit the `step_limit`
  (25) so `exit_status` is `LimitsExceeded`, but the hidden test matrix still
  passed, so the verdict is a legitimate PASS.

## Notes / honesty

- **2 tasks**, not 5-10: the two upstream repos used here are small, pure-Python
  and reproducible. A third candidate (`click__click-3578`, "double-bracketing
  of choices") was built and its fix/test extracted, but its test file
  (`tests/test_basic.py`) uses `itertools.chain` in `pytest.mark.parametrize`,
  which triggers `PytestRemovedIn10Warning` — and click's `filterwarnings =
  error` turns that into a collection error under pytest >= 8.2. It was dropped
  rather than shipping an unverifiable task.
- HuggingFace (source of the official SWE-bench dataset) was unreachable from
  this network; tasks were reconstructed from real git history instead (each
  `base_commit`/`patch`/`test_patch` is a real upstream commit).
- Validation is reproducible: `uv run python scripts/build_swebench_subset.py`
  re-checks that every FAIL_TO_PASS test fails on the buggy baseline and passes
  after the gold patch, and that PASS_TO_PASS stays green.
