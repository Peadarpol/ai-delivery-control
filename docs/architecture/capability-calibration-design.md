# Capability Calibration Design (T1-G-14)

This design specification details the architecture for per-capability calibration weighting to address the balance between gate correctness and developer permissiveness (AT9 Calibration Gate).

---

## 1. AT9 Problem Statement
In a multi-persona gating architecture, treating all domain constraints with uniform severity leads to sub-optimal developer friction or critical security escapes. A gate that is too strict in standard domains (e.g. style/formatting) triggers high false-positive rates and developer fatigue. Conversely, a gate that is too permissive in high-risk domains (e.g. database transactions or tenant isolation) risks merging catastrophic failures. The AT9 calibration gate aims to dynamically and statically adjust the gate's decision weights on a per-capability/domain basis.

---

## 2. Per-Domain Cost-of-False-Negative (CFN)
Under-weighting certain capabilities leads to higher business risks. The table below outlines the risk weights assigned to key domains:

| Domain / Capability | Cost of False Negative (CFN) | Priority | Impact of Escape |
|---------------------|-----------------------------|----------|------------------|
| **Branch Isolation** | Critical (1.0) | Highest | Cross-tenant data leak, compliance failure |
| **Security & Auth** | Critical (1.0) | Highest | Privilege escalation, authentication bypass |
| **Database Transactions** | High (0.8) | High | Corrupted state, lock contention, deadlocks |
| **Schema Hardening** | Medium (0.5) | Medium | Untyped inputs, API validation mismatch |
| **Code Quality** | Low (0.2) | Low | Style violations, dead code, minor lint issues |

---

## 3. Proposed Configuration Schema
When implemented in v1.4.0, the schema will support developer-configured overrides in `.agent/config.yaml`.

> [!WARNING]
> Do NOT add this block to `.agent/config.yaml` in the current release. This is for schema documentation only.

```yaml
# Proposed v1.4.0 Calibration Override Schema
capabilities:
  calibration:
    enabled: true
    weights:
      branch-isolation: 1.0
      security-audit: 1.0
      database-design: 0.8
      schema-hardening: 0.5
      code-review: 0.2
    rebuttal_decay_days: 30
```

---

## 4. Required Behavior Spec for `ai_review.py`
When the `capabilities.calibration` configuration is active:
1. The review gate loads the per-domain weights from configuration.
2. For each detected gate issue, the score penalty is multiplied by its domain weight:
   $$\text{Penalty}_{\text{calibrated}} = \text{Penalty}_{\text{base}} \times \text{Weight}_{\text{domain}}$$
3. If the cumulative penalty exceeds the gate's failure threshold (typically `1.0`), the gate issues a `FAIL` verdict.
4. If a domain weight is set to `0.0`, any issues detected within that domain are demoted to `ADVISORY` and do not block the commit.

---

## 5. Calibration Data Source: Rebuttal Rate
To prevent developer gaming, the calibration system uses past rebuttal statistics from `.ai-review-log.jsonl` as feedback:
- **High Agent Rebuttal Rate (>15%)**: Indicates the agent is repeatedly challenging gate findings in a specific domain. The system should automatically elevate that domain's weight (correctness bias) to audit the agent more closely.
- **High Human Rebuttal Rate (>15%)**: Indicates developers are repeatedly overriding the gate due to false positives. The system should recommend lowering the domain weight (permissiveness bias) to reduce friction.

---

## 6. AT9 Decision Block

- **Finding** — Uniform severity gating causes high developer friction in low-risk domains and security exposures in high-risk domains.
- **Tradeoff** — Correctness (enforcing strict gates everywhere) vs. Permissiveness (allowing fast commits in low-risk domains).
- **Exposes** — FM9 (Calibration Failure: high friction leading to developer hook bypass, or loose gates leaking security vulnerabilities).
- **Remediation** — Implement per-capability calibration weighting (T1-G-14) using cost-of-false-negative coefficients and rebuttal rate feedback.
