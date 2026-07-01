# PLAN — code-review/SKILL.md Universal/Project Split (v1.4.6 follow-on)

**Status**: READY FOR EXECUTION — pick up as the first task of a fresh session
**Created**: 2026-06-30 (Updated 2026-07-01 based on Peter's review feedback)
**Context**: Continuation of the universal-vs-project skill content leak cleanup that began on branch `refactor/ai-review-decomposition`. This is the third and final leaked-content item identified during the Step 6.3 grep audit.

**Why this one is different**: `code-review/SKILL.md` contains Passes 4-8 (~200 lines) of GymBase business-rule content — RBAC specifics, branch isolation and `X-Gym-Branch-ID`, the BR-* business rule table, financial cents precision, and Pydantic schema hardening. This requires **extraction, modular decomposition, and merge relocation** to keep universal skills generic and consumer projects compliant.

**Two-repo scope**: approved by the human architect to resolve the sync gap between `ai-delivery-control` (the universal skill) and `Gym_App` (the GymBase-specific overlay destination).

---

## Pre-flight (run first, before any edits)

```powershell
cd C:\projects\ai-delivery-control
git checkout main
git pull
git log --oneline -5
```

Confirm `refactor/ai-review-decomposition` has merged to main. If not, branch from the decomposition branch.

```powershell
git checkout -b refactor/code-review-skill-split
python -m pytest --tb=short -q
```

Record the baseline test count (must match 372 passed or current main count).

Read all files in full:
- `C:\projects\ai-delivery-control\.agent\skills\universal\code-review\SKILL.md`
- `C:\projects\Gym_App\.agent\skills\code-review\SKILL.md`
- `C:\projects\Gym_App\src\scripts\review_context_project.md`

---

## COMMIT 1 — Split and Decouple the Harness Universal Skills

**Repository**: `ai-delivery-control`

### 1.1 Decompose `.agent/skills/universal/code-review/SKILL.md`
Remove these passes entirely to keep it language-agnostic and **<150 lines**:
- **Pass 4 (RBAC & Auth)**: merge its generic pattern into `security-audit/SKILL.md`.
- **Pass 5 (Multi-Tenant & Branch Isolation)**: extract its generic pattern to the new `branch-isolation` skill.
- **Pass 6 (Business Rule Invariants)**: drop entirely (re-scaffolded in project context).
- **Pass 7 (Financial Precision)**: drop specific cents/GST rules. Keep a 2-3 line generic placeholder pass.
- **Pass 8 (Schema Hardening)**: extract its generic pattern to the new `schema-hardening` skill.

**Renumber remaining passes sequentially**:
- Pass 1 — Context & Purpose (unchanged)
- Pass 2 — Architecture & Layer Violations (unchanged)
- Pass 3 — Exception Handling (unchanged)
- Pass 4 — Correctness & Logic (was Pass 9, includes hallucination checks)
- Pass 5 — Security (was Pass 10, includes hallucination checks)
- Pass 6 — Performance (was Pass 11)
- Pass 7 — Testing (was Pass 12)
- Pass 8 — Documentation & Hygiene (was Pass 13)

Update checklist, title, and description frontmatter (remove GymBase paths from `requires-context`).

### 1.2 Create [NEW] `.agent/skills/universal/branch-isolation/SKILL.md`
- **Frontmatter**: `name: branch-isolation`, `version: 1.0.0`, `skill_type: universal`.
- Define generic patterns for tenant isolation (branch scoping, query scoping, middleware validation).
- Include cross-reference to `governance.md §2` escalation triggers for high-risk data-isolation changes.
- Add a structured **Anti-Rationalisation Table** (excuse vs. rebuttal).
- Ensure length is **<150 lines**.

### 1.3 Create [NEW] `.agent/skills/universal/schema-hardening/SKILL.md`
- **Frontmatter**: `name: schema-hardening`, `version: 1.0.0`, `skill_type: universal`.
- Define generic patterns for input validation, extra field restriction (`extra="forbid"` to prevent mass-assignment), and custom validations.
- Add a structured **Anti-Rationalisation Table**.
- Ensure length is **<150 lines**.

### 1.4 Merge generic RBAC checks and Genericise `.agent/skills/universal/security-audit/SKILL.md`
- Port the generic RBAC patterns from the old Pass 4 (endpoint protection, SYSTEM_ADMIN bypass safety, table isolation, IDOR prevention) into the existing workflow of `.agent/skills/universal/security-audit/SKILL.md`.
- Add cross-reference to `governance.md §2` escalation triggers.
- Add a structured **Anti-Rationalisation Table** for RBAC/auth bypasses.
- **Clean up Pre-existing Leaks in `security-audit/SKILL.md`**:
  - Replace bare entity names (`User`, `Staff`, `Contact`, `Invoice`, `Payment`, `Contract`) with generic placeholders/bracketed placeholder text (e.g. `the entity/resource being accessed`, `financial records`, `<sensitive entity, e.g. User/Order/Invoice>`).
  - Replace literal paths (`src/application/api/`, `src/application/dtos/`) with placeholder/example framing ("your API route layer", "your Pydantic DTO layer").
  - Remove the "overlapping contract dates" example (verbatim BR-CON-01) — replace with a generic business-logic-flaw example (e.g., "double-booking or double-spending patterns specific to your domain").

### 1.5 Update `verification-before-completion/SKILL.md`
- Add a structured **Anti-Rationalisation Table** addressing test/validation bypasses.

### 1.6 Generate Checksums
Do not edit `manifest.py` or `install.py` (they auto-copy via globs). Instead, update the checksums database:
```powershell
python bootstrap/generate_checksums.py
```
Verify `bootstrap/checksums.py` contains SHA-256 entries for the two new files: `.agent/skills/universal/branch-isolation/SKILL.md` and `.agent/skills/universal/schema-hardening/SKILL.md`.

### Verification for Commit 1
```powershell
Select-String -Path ".agent\skills\universal\code-review\SKILL.md" -Pattern "Gym App|branch_id|StaffRole|UserRole|BR-CON|BR-POS|BR-AUD|X-Gym-Branch-ID|HardenedBaseModel"
# Expected: no output

Select-String -Path ".agent\skills\universal\security-audit\SKILL.md" -Pattern "\b(User|Staff|Contact|Invoice|Payment|Contract)s?\b" -CaseSensitive
# Expected: no output (bare entities should be cleaned or bracketed placeholders)

python -m pytest --tb=short -q
# Expected: all tests pass
```

### Commit 1 message
```
fix(skills): split code-review SKILL.md and create modular universal skills

Decomposed monolithic code-review/SKILL.md down to Passes 1-3 and 9-13 (renumbered to 1-8) to keep it under 150 lines and language-neutral.

Extracted generic multi-tenant query isolation and schema mass-assignment patterns into two new universal skills:
- branch-isolation/SKILL.md
- schema-hardening/SKILL.md

Merged generic RBAC checks into security-audit/SKILL.md, and genericised security-audit/SKILL.md to remove bare GymBase entities (User, Staff, Contract) and literal paths.

Added anti-rationalisation tables across security-audit, verification-before-completion, branch-isolation, and schema-hardening.

Regenerated and registered new skill file checksums in bootstrap/checksums.py.
```

---

## COMMIT 2 — Merge GymBase specific rules into review_context_project.md (Gym_App repo)

**Repository**: `Gym_App`

```powershell
cd C:\projects\Gym_App
git checkout devops
git pull
git checkout -b chore/code-review-skill-content-migration
```

**File**: `src/scripts/review_context_project.md`

### What to do
Do not simply paste the old Passes 4-7. Merge the rules cleanly against existing sections:

- **RBAC**: Merge the SYSTEM_ADMIN short-circuit rule, table-isolation rule, and IDOR prevention rule *into* the existing `[RULE:RBAC-HIERARCHY]` section as additional sub-rules, rather than creating a second RBAC section.
- **Branch Isolation**: Merge the `X-Gym-Branch-ID` middleware rule, the `BranchSettingsResolver` carve-out, and the `business_id` listener safety net *into* the existing `[RULE:MULTI-TENANCY]` section, reconciling with the existing Rule 1–3 numbering.
- **Mass Assignment**: Skip the port (redundant; `[RULE:MASS-ASSIGNMENT]` already covers it).
- **BR-* Rules and Financial Precision**: Add these as new sections at the bottom following the file's conventions.

Add a changelog entry at the top of the file documenting the merge:
```
>   v2.2 — Merged RBAC, branch isolation, business rule table, and financial
>           precision content from the harness's universal code-review/SKILL.md
>           (which was split to remove GymBase-specific content per the
>           universal/project leak cleanup). This content lives here as the single
>           source of truth for GymBase's project-specific review invariants.
```

### Verification for Commit 2
```powershell
python -m pytest --tb=short -q
# Confirm test suite is unaffected
```

### Commit 2 message
```
chore(review-context): merge RBAC/branch-isolation/BR-rules from code-review skill

Relocated GymBase-specific rules (SYSTEM_ADMIN short-circuit, table isolation, IDOR prevention, branch-isolation carve-outs, business rule table, and integer-cents financial rules) from the harness universal code-review skill into review_context_project.md.

Merged the RBAC and branch isolation rules into existing [RULE:RBAC-HIERARCHY] and [RULE:MULTI-TENANCY] sections rather than duplicating them.
```

---

## COMMIT 3 — Sync the corrected universal code-review/SKILL.md to GymBase

**Repository**: `Gym_App`, same branch as Commit 2.

**File**: `.agent/skills/code-review/SKILL.md`

### What to do
Copy the harness's now-split, now-generic `code-review/SKILL.md` over GymBase's copy:
```powershell
Copy-Item "C:\projects\ai-delivery-control\.agent\skills\universal\code-review\SKILL.md" "C:\projects\Gym_App\.agent\skills\code-review\SKILL.md" -Force
```
This syncs the generic structure, current frontmatter, and the four AI hallucination checks to GymBase.

### Verification for Commit 3
```powershell
python -m pytest --tb=short -q
Select-String -Path ".agent\skills\code-review\SKILL.md" -Pattern "API hallucination check|latent race condition|implicit security vulnerability|architectural technical debt"
# Expected: 4 matches
```

### Commit 3 message
```
sync: pull updated code-review SKILL.md from harness (v1.4.6 split + hallucination checks)

GymBase's local copy of code-review/SKILL.md was stale. Syncing it brings the new genericized passes, frontmatter metadata, and the four AI hallucination checks (API hallucination, latent race conditions, implicit security vulnerabilities, architectural technical debt).
```

---

## COMMIT 4 — Remove stale GymBase Codes Community links

**Repository**: `ai-delivery-control`, same branch as Commit 1.

### What to do
Run a search to confirm the trailing source attribution pattern exists in the 13 files:
```powershell
Select-String -Path ".agent\skills\universal\*\SKILL.md" -Pattern "GymBase Codes Community"
```
Ensure the following 13 files are matched:
- `api-design`, `code-migration`, `database-design`, `debugging`, `devops-cicd`, `performance-optimization`, `python-async`, `python-automation`, `python-fastapi`, `python-testing`, `refactoring`, `test-writing`, `testing-patterns`.

For each matched file, remove the trailing `*Source: [GymBase Codes Community](https://GymBase.codes/rules/<slug>)*` line, along with the preceding `---` separator if it leaves a dangling empty block.

Run the checksums generator to update the registered digests:
```powershell
python bootstrap/generate_checksums.py
```

### Verification for Commit 4
```powershell
Select-String -Path ".agent\skills\universal\*\SKILL.md" -Pattern "GymBase Codes Community"
# Expected: no output
```

### Commit 4 message
```
chore(skills): remove stale GymBase Codes Community attribution links

Removed the trailing "Source: GymBase Codes Community" attribution line from
13 universal skill files where it no longer reflects actual provenance.
Cosmetic-only change, no content or behaviour affected.

Regenerated bootstrap/checksums.py to reflect the 13 modified files.
```

---

## Final verification (both repos)

**ai-delivery-control**:
```powershell
cd C:\projects\ai-delivery-control
python -m pytest --tb=short -q
python bootstrap/validate.py --project-path .
```

**Gym_App**:
```powershell
cd C:\projects\Gym_App
python -m pytest --tb=short -q
python .agent/skills/senior-architect/scripts/architecture_checks.py
```

Both must show clean results matching their respective baselines.

---

## Documentation updates

**ai-delivery-control — `docs/planning/FRAMEWORK_BACKLOG.md`**:
Update the v1.4.6 section to mark the `code-review/SKILL.md` cleanup item as complete.

**ai-delivery-control — `docs/planning/CAPABILITY_INVENTORY.md`**:
Update the code-review skill capability card to note the split structure.

---

## Stop condition

Do NOT push either branch. Do NOT raise PRs. Stop after Commit 4 and final verification, and report:
1. All 4 commit SHAs (2 in ai-delivery-control, 2 in Gym_App)
2. Commit 1 grep verification output (verifying no Gym App terms in `code-review/SKILL.md` and no bare entities in `security-audit/SKILL.md`)
3. Commit 3 grep verification output (4 matches for hallucination checks in GymBase `code-review/SKILL.md`)
4. Commit 4 grep verification output (13 matches before, 0 after for `GymBase Codes Community` links)
5. Both repos' test suite pass/fail counts compared to their baselines
6. Confirmation of Pass-number grep check results
