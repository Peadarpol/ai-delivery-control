# AT-05 — `_strip_json_fences` Regression Forensics

This document presents a post-mortem analysis of the `_strip_json_fences` NameError regression (**F5**).

## 1. Regression Root-Cause & Commit Forensics

- **Defect Introduction Commit**: `8b6ae2a3ad53b3a8e1b2e935bb0a99ef70d18c17` (titled: *"Fix JSON parser robustness and max_tokens limit in providers --no-trace JSON parse fix"*, dated July 9, 2026).
- **Incident Description**:
  - The commit refactored provider responses to introduce a unified `_parse_json_response(raw)` helper inside `src/scripts/providers.py` to parse JSON and extract content from braces.
  - The refactoring deleted the `_strip_json_fences` function completely from the module namespace.
  - However, the refactoring **failed** to update calls to `_strip_json_fences` inside the `raw_completion` methods of all three concrete providers: `AnthropicProvider`, `OpenAIProvider`, and `OllamaProvider`.
  - As a result, calling `raw_completion` raised `NameError: name '_strip_json_fences' is not defined`.
- **Meta-Governance Observation**:
  - The removing commit was passed with the `--no-trace` commit message bypass.
  - No adversarial AI review log entry exists for this commit, indicating that the hooks were bypassed at commit time using `git commit --no-verify` or standard command bypasses.
  - This highlights the vulnerability of client-side pre-commit checks to direct developer bypasses, which can result in fatal NameErrors entering the codebase without AI gate scrutiny.

---

## 2. Expected Call Contract & Verbatim Body

### Consumers of `raw_completion`
There are three script consumers that invoke `raw_completion` and expect clean JSON back:
1. **`rebuttal.py`** (Line 484): calls `provider.raw_completion(REBUTTAL_SYSTEM_PROMPT, user_content)` and passes the string directly to `json.loads(raw_response)`.
2. **`pm_scaffold.py`** (Line 268): calls `provider.raw_completion(system_prompt, user_content)` and parses the output.
3. **`acceptance_check.py`** (Line 225): calls `provider.raw_completion(system_prompt, user_content)` and executes `json.loads(raw_resp)`.

If the provider returns fenced JSON (enclosed in markdown blocks like ` ```json ... ``` `), passing it directly to `json.loads()` raises a `JSONDecodeError`. Therefore, the `raw_completion` interface method MUST strip markdown fences.

### Verbatim Original Function Body
Recovered from git history prior to deletion (commit `5df2c97`):
```python
def _strip_json_fences(raw: str) -> str:
    """Strip markdown code fences and extraneous text if the model wraps JSON in them."""
    first_brace = raw.find('{')
    last_brace = raw.rfind('}')
    if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
        return raw[first_brace:last_brace+1]
    return raw
```

---

## 3. Test-Gap Audit

The regression slipped through the test suite because of:
1. **Excessive Mocking**: External scripts mocking the provider layer stubbed out `provider.raw_completion` completely (e.g. `mock_provider.raw_completion.return_value = json.dumps(...)`), avoiding invocation of the actual concrete class methods.
2. **Missing Integration Tests**: The unit tests in `tests/test_providers.py` only checked provider metadata and availability checks; they did not test `raw_completion` against stubbed HTTP network boundaries to verify that it parsed, cleaned, and returned the correct data format.

### Resolution
We have added a strict xfail integration test reproducing this NameError crash under `TestProvidersRawCompletionRegression` in [tests/test_providers.py](file:///c:/projects/ai-delivery-control/tests/test_providers.py) and registered a new golden dataset regression test case under `GD-004` in [.agent/evals/golden_dataset.yaml](file:///c:/projects/ai-delivery-control/.agent/evals/golden_dataset.yaml).
