# ID Map Table — First-Commit & Onboarding Defects (v1.4.10 Workstream)

This document establishes the official traceability anchors for the first-commit and cold-start onboarding defects identified in synthetic reproductions and the live user observation session.

## Defect to Backlog ID Mapping

| Failure ID | Backlog / HIB ID | Title / Component | Target Release | Governing Workflow / Routing |
| :--- | :--- | :--- | :--- | :--- |
| **F1** | `HIB-070` | `pip run` template rendering bug | v1.4.9.1 | installer/template (F-COLD-2 extends AT-01) |
| **F2** | `HIB-071` | `ai_review.py` Pydantic import-time crash | v1.4.9.1 | gate runtime (F-COLD-3 extends AT-02) |
| **F3** | `HIB-072` | `architecture_checks.py` `harness_utils` pathing | v1.4.9.1 | hook wiring (AT-03 audit) |
| **F4** | `T1-K-15` | Exception Standards GymBase leak / precondition | v1.4.10 | template design (absorbed into T1-K-14 taxonomy) |
| **F5** | `HIB-069` | `providers.py` `NameError: _strip_json_fences` | v1.4.9.1 | runtime regression (AT-05 forensics) |
| **F6** | `T1-L-23` | Traceability gate root commit / bypass ergonomics | v1.4.10 | gate design (coordinated with T1-K-13 / HIB-061) |
| **F7** | `T1-K-16` | Mutating framework-owned files (black/ruff) | v1.4.11 | template policy |
| **F8** | `T1-K-17` | Validator dry-run design (presence to runnability) | v1.4.11 | validator design (feeds F-COLD-1/3/5 into AT-08) |
| **F-COLD-1** | `T1-B-14` | Onboarding target validation check | v1.4.11 | validator self-check + docs (feeds AT-08) |
| **F-COLD-2** | `T1-B-15` | macOS/venv path and interpreter assumptions | v1.4.11 | template/design fix (extends AT-01 rendering matrix) |
| **F-COLD-3** | `T1-B-16` | API key discovery & reachability preflight check | v1.4.11 | installer feature + validator (extends AT-02/AT-08) |
| **F-COLD-4** | *None* | Retrofit mode (vibe-coded prototype onboarding) | Unscheduled | Proposed new workstream (logged under "Under Consideration") |
| **F-COLD-5** | `T1-B-17` | Stale venv Python downgrades tooling | v1.4.11 | validator currency checks (feeds AT-08) |

---

> [!NOTE]
> **Namespace Safety**: All assigned `HIB-*` and `T1-*` IDs have been scanned against both `FRAMEWORK_BACKLOG.md` and `harness_improvement_backlog.md` using automated scripts to guarantee zero ID collisions.
