# Project-Specific AI Review Invariants

## 1. Config Defaults
**Config access**: call sites must not pass `default=` for keys in the central DEFAULTS registry (`harness_utils.py`); absent call-site fallbacks are by design (resolution: config -> DEFAULTS -> explicit -> None).
