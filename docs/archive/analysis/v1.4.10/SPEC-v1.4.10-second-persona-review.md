# Second Multi-Persona Adversarial Review Report: SPEC-v1.4.10-governance-hardening

**Target Artifact**: [SPEC-v1.4.10-governance-hardening.md](file:///c:/projects/ai-delivery-control/docs/planning/specs/SPEC-v1.4.10-governance-hardening.md)  
**Review Date**: 2026-07-20  
**Reviewing Personas**:
1. 🏗️ **Enterprise Integration Architect**
2. 🚀 **Performance & Concurrency Specialist**
3. 🧹 **Refactoring & Clean Architecture Specialist**
4. 🧠 **AI Agent Behavioral & Safety Researcher**

---

## Executive Summary

Following the first multi-persona review, this second review evaluates [SPEC-v1.4.10-governance-hardening.md](file:///c:/projects/ai-delivery-control/docs/planning/specs/SPEC-v1.4.10-governance-hardening.md) from four additional advanced perspectives: Enterprise Integration, Performance/Concurrency, Clean Architecture, and AI Behavioral Safety.

This review identified **1 Security/Jailbreak Loophole**, **2 Enterprise Topology Risks**, **2 Performance/Caching Hazards**, and **2 Clean Architecture Cleanups**.

---

## 1. 🏗️ Enterprise Integration Architect Review

### Finding EIA-1 (HIGH): Git Worktree & Nested Directory Path Resolution Flaw (`T1-K-13.1`)
* **Location**: Section 5, Component: Requirement Traceability (`check_traceability.py`, line 149).
* **Defect**: Executing `git show HEAD:docs/...` assumes pathing relative to the repository root. In Git worktrees (where `.git` is a file, not a directory) or when pre-commit runs from a nested subdirectory, relative path lookups fail with `path 'docs/...' does not exist in 'HEAD'`.
* **Remediation**:
  All git path queries in `check_traceability.py` MUST resolve repository-root relative paths by resolving `git rev-parse --show-toplevel` first: `git show HEAD:<repo_relative_path>`.

### Finding EIA-2 (MEDIUM): Non-Interactive CI Environment Attribution (`init_session.py`)
* **Location**: Section 5, Component: Requirement Traceability (`init_session.py`, line 142).
* **Defect**: In non-interactive CI environments (GitHub Actions, GitLab CI) where no parent session exists, `signed_by` falls back to `null`/empty.
* **Remediation**:
  In non-interactive environments, `init_session.py` MUST inspect standard CI environment variables (`GITHUB_ACTOR`, `GITLAB_USER_LOGIN`, `GIT_AUTHOR_NAME`) to populate `signed_by` alongside `"is_interactive": false`.

---

## 2. 🚀 Performance & Concurrency Specialist Review

### Finding PCS-1 (MEDIUM): Cache Invalidation Failure on Config Mutation (`T1-E-04`)
* **Location**: Section 5, Component: Configuration Loading (`harness_utils.py`, line 114).
* **Defect**: The module-level `_config_cache` dict keys by path without checking file modification time (`mtime`). If a test or dynamic task mutates `.agent/config.yaml` during execution, cached values will return stale config data.
* **Remediation**:
  `_config_cache` MUST store a tuple of `(mtime, config_dict)` and invalidate the cache if `os.path.getmtime(path)` differs from the cached timestamp.

### Finding PCS-2 (LOW): Subprocess Spawning Overhead on Windows
* **Location**: Section 5 & Section 7 (pre-commit execution latency).
* **Defect**: Invoking multiple sequential `git` CLI calls during `commit-msg` hooks on Windows creates noticeable shell latency (150ms-300ms per commit).
* **Remediation**:
  Batch git predicate calls where possible (e.g. combining `git rev-parse --show-toplevel --verify HEAD` into a single subprocess execution).

---

## 3. 🧹 Refactoring & Clean Architecture Specialist Review

### Finding RCA-1 (MEDIUM): Monolithic God-Object Risk in `DEFAULTS` Table (`T1-E-04`)
* **Location**: Section 5, Component: Configuration Loading (`harness_utils.py`, line 110).
* **Defect**: Placing defaults for 20+ distinct subsystems into a single flat `DEFAULTS` dictionary creates tight coupling across unrelated modules.
* **Remediation**:
  Construct `DEFAULTS` inside `harness_utils.py` by composing modular section dictionary constants (e.g. `ROUTING_DEFAULTS`, `TRACEABILITY_DEFAULTS`), maintaining domain isolation.

### Finding RCA-2 (LOW): Duplicate Fallback Parser Maintenance (`migration_base.py`)
* **Location**: Section 5, Component: Configuration Loading (line 116).
* **Defect**: Duplicating fallback parsing logic between `bootstrap/migration_base.py` and `harness_utils.py`.
* **Remediation**:
  Specify that `bootstrap/migration_base.py` will be updated to reuse `harness_utils.load_yaml_with_fallback` once `v1.4.10` is released.

---

## 4. 🧠 AI Agent Behavioral & Safety Researcher Review

### Finding AIB-1 (HIGH): Root-Commit Exemption Orphan-Branch Loophole (`AT-06` / `HIB-061`)
* **Location**: Section 4, Scenario 5 & Section 5 (`check_traceability.py`, line 150).
* **Defect**: Checking whether `git rev-parse --verify HEAD` fails is true for **orphan branches** (`git checkout --orphan <branch>`), not just zero-commit repositories! An agent could create an orphan branch in an existing repository to trigger `is_root_commit() == True` and bypass traceability rules on arbitrary commits.
* **Remediation**:
  The `is_root_commit()` predicate MUST verify **total repository commit count == 0** (`git rev-list --all --count` returning `0`), NOT just current branch `HEAD` unresolution.

### Finding AIB-2 (MEDIUM): Prompt Injection Surface in `--ack-no-trace` Reason Strings (`T1-K-13`)
* **Location**: Section 5, Component: Requirement Traceability (line 165).
* **Defect**: Unsanitized user/agent text in `--ack-no-trace "<reason>"` written directly to `harness_events.jsonl` could contain prompt-injection payloads that compromise downstream LLM tools reading event logs.
* **Remediation**:
  All `--ack-no-trace` reason strings MUST be sanitized (stripping system instructions, markdown/XML control structures, and limiting string length to 250 characters) before logging to `harness_events.jsonl`.

---

## Consensus & Action Plan

| ID | Persona | Severity | Target Section | Action |
|---|---|---|---|---|
| **AIB-1** | AI Safety Researcher | **HIGH** | Section 4 & 5 (`AT-06`) | Harden `is_root_commit()` predicate to check `git rev-list --all --count == 0` (preventing orphan branch bypasses). |
| **EIA-1** | Enterprise Architect | **HIGH** | Section 5 (`T1-K-13.1`) | Anchor git path lookups to `git rev-parse --show-toplevel` for worktree support. |
| **AIB-2** | AI Safety Researcher | **MEDIUM** | Section 5 (`T1-K-13`) | Sanitize `--ack-no-trace` reason strings before writing to `harness_events.jsonl`. |
| **EIA-2** | Enterprise Architect | **MEDIUM** | Section 5 (`init_session.py`) | Map non-interactive CI attribution to `GITHUB_ACTOR` / `GITLAB_USER_LOGIN` / `GIT_AUTHOR_NAME`. |
| **PCS-1** | Performance Specialist | **MEDIUM** | Section 5 (`harness_utils.py`)| Add mtime validation to `_config_cache` to prevent stale cache hits on disk edits. |
| **RCA-1** | Refactoring Specialist| **MEDIUM** | Section 5 (`harness_utils.py`)| Modularize `DEFAULTS` table using domain-specific dict constants. |
| **PCS-2** | Performance Specialist | **LOW** | Section 5 & 7 | Batch git CLI predicate calls to minimize Windows process creation overhead. |
| **RCA-2** | Refactoring Specialist| **LOW** | Section 5 (`migration_base.py`) | Reuse `load_yaml_with_fallback` in `migration_base.py`. |

---
