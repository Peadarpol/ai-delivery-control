# AT-05 — `_strip_json_fences` Regression Forensics

This document presents a post-mortem analysis of the `_strip_json_fences` NameError regression (**F5**).

## 1. Regression Root-Cause & Commit Forensics

- **Defect Introduction Commit**: `8b6ae2a3ad53b3a8e1b2e935bb0a99ef70d18c17` (titled: *"Fix JSON parser robustness and max_tokens limit in providers --no-trace JSON parse fix"*, dated July 9, 2026).
- **Incident Description**:
  - The commit refactored provider responses to introduce a unified `_parse_json_response(raw)` helper inside `src/scripts/providers.py` to parse JSON and extract content from braces.
  - The refactoring deleted the `_strip_json_fences` function completely from the module namespace.
  - However, the refactoring **failed** to update calls to `_strip_json_fences` inside the `raw_completion` methods of all three concrete providers: `AnthropicProvider`, `OpenAIProvider`, and `OllamaProvider`.
  - As a result, calling `raw_completion` raised `NameError: name '_strip_json_fences' is not defined`.
- **Meta-Governance & Git History Clarification**:
  - A review of decisions log entry history confirms that the commit `8b6ae2a` was the approved follow-up fix that resolved the JSON parser issues. The `--no-trace` keyword in the commit message was descriptive context, not a hook bypass indicator.
  - The previous assertion that the commit bypassed hooks via `--no-verify` is unproven; additionally, the `.ai-review-log.jsonl` file was not tracked in git at that point in history, meaning its absence cannot be used as evidence of gate skipping.
  - **Meta-Analytical Lesson**: The first draft of this analysis contained a citation-based hallucination. It accurately cited commit `5df2c97` but fabricated the function body as a brace-extraction algorithm (copying it from the still-existing `_parse_json_response` function) instead of extracting the real regex-based body from git history. This illustrates the risk of "confident but wrong" AI output where citations are valid but content is confabulated.

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
    """Strip markdown code fences if the model wraps JSON in them."""
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw
```

---

## 3. Test-Gap Audit

The regression slipped through the test suite because of:
1. **Excessive Mocking**: External scripts mocking the provider layer stubbed out `provider.raw_completion` completely (e.g. `mock_provider.raw_completion.return_value = json.dumps(...)`), avoiding invocation of the actual concrete class methods.
2. **Missing Integration Tests**: The unit tests in `tests/test_providers.py` only checked provider metadata and availability checks; they did not test `raw_completion` against stubbed HTTP network boundaries to verify that it parsed, cleaned, and returned the correct data format.

### Resolution
We have added a strict xfail integration test reproducing this NameError crash under `TestProvidersRawCompletionRegression` in [tests/test_providers.py](file:///c:/projects/ai-delivery-control/tests/test_providers.py) and registered a new golden dataset regression test case under `GD-004` in [.agent/evals/golden_dataset.yaml](file:///c:/projects/ai-delivery-control/.agent/evals/golden_dataset.yaml).
