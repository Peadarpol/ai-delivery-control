# v1.4.6 Release Instruction — ai\_review.py Decomposition \+ Universal Skill Cleanup

**Repository**: `C:\projects\ai-delivery-control` **Branch**: cut `refactor/ai-review-decomposition` from `main` (after v1.4.5 has merged) **Theme**: This was not a planned backlog item — it is a side-effect cleanup. ai\_review.py grew to 141.6KB (6.7x the next-largest file in src/scripts/) through organic accretion across v1.0.0–v1.4.5. This release extracts cohesive units into existing/new modules with ZERO behaviour change, plus cleans up two universal skills that leaked GymBase-specific content. The goal is a clean slate before v1.5.0 begins.

**Critical constraint**: This is a pure refactor. No behavioural change is permitted. Every extracted function must be called with identical signatures and identical behaviour from `ai_review.py` after extraction. The full test suite must pass identically before and after each commit — any test count change other than newly added tests is a STOP condition.

---

## Standing documentation rule

After each commit, update `docs/planning/FRAMEWORK_BACKLOG.md`, `docs/planning/CAPABILITY_INVENTORY.md`, and (final commit only) `docs/planning/FRAMEWORK_ROADMAP.md` in the same commit — not a separate docs commit.

---

## Prerequisites

cd C:\\projects\\ai-delivery-control

git checkout main

git pull

git log \--oneline \-3

Confirm v1.4.5 is merged (commit message containing "release: v1.4.5" should be visible).

git checkout \-b refactor/ai-review-decomposition

python \-m pytest \--tb=short \-q \> /tmp/baseline\_test\_output.txt 2\>&1

Record the baseline pass/fail count from this run — every subsequent commit's test run must match it exactly (plus any newly added tests for the new modules).

Read the full current `src/scripts/ai_review.py` before starting (already done in this session — 141.6KB, \~2000 lines). Read `src/scripts/roster_builder.py` in full as well, since Commit 1 merges functions into it.

---

## COMMIT 1 — Extract roster management into roster\_builder.py

**Theme**: `_load_branch_isolation_config()`, `_ensure_and_load_model_roster()`, and `verify_and_suppress_roster_issues()` are roster-domain logic living in the wrong file. `roster_builder.py` already exists and already contains `build_branch_isolation_roster()` — these three functions belong alongside it.

**Files to modify**:

- `src/scripts/roster_builder.py` (add three functions)  
- `src/scripts/ai_review.py` (remove three functions, replace with thin delegating calls)

---

### Step 1.1 — Move functions to roster\_builder.py

Append the following three functions to `src/scripts/roster_builder.py`, after the existing `build_branch_isolation_roster()` function. Copy them **exactly** from `ai_review.py` — do not alter any logic, only adjust imports as needed:

1. `_load_branch_isolation_config() -> Tuple[List[str], List[str]]`  
2. `_ensure_and_load_model_roster() -> Dict[str, Any]`  
3. `verify_and_suppress_roster_issues(typed_verdict, route_decision) -> None`

These functions reference `PROJECT_ROOT`, `_setup_sys_path`, `build_branch_isolation_roster`, `json`, `glob`, `os`, `Path`. Verify `roster_builder.py` either already imports these or add the necessary imports at the top of the file. `PROJECT_ROOT` in `roster_builder.py` may need its own `_find_project_root()`\-equivalent if not already present — check the existing file first; if it already resolves `PROJECT_ROOT` via a shared mechanism, reuse it rather than duplicating the resolution logic.

`verify_and_suppress_roster_issues()` references `ReviewVerdict` and `RouteDecision` types from `ai_review.py` (Pydantic models). To avoid a circular import, type these parameters as `Any` in `roster_builder.py` rather than importing the Pydantic models — the function only accesses `.issues`, `.blocking_concern`, `.verdict` attributes dynamically, so this is safe and matches the existing dynamic-typing pattern already used elsewhere in the module loading section of `ai_review.py` (the `try: import X except ImportError` pattern).

### Step 1.2 — Replace in ai\_review.py with delegating wrappers

In `ai_review.py`, remove the three function bodies entirely. Replace each call site and definition with a thin import-and-delegate pattern matching the existing style already used for `extract_adr_annotations`, `run_co_change_estimator`, `get_provider`, etc. (see the "Framework modules imported dynamically" section near the top of the file):

def \_load\_branch\_isolation\_config() \-\> Tuple\[List\[str\], List\[str\]\]:

    if roster\_builder is not None and hasattr(roster\_builder, "\_load\_branch\_isolation\_config"):

        return roster\_builder.\_load\_branch\_isolation\_config()

    return \["src/\*\*/models.py", "src/\*\*/model.py"\], \["BranchAwareMixin", "BranchIsolatedMixin"\]

def \_ensure\_and\_load\_model\_roster() \-\> Dict\[str, Any\]:

    if roster\_builder is not None and hasattr(roster\_builder, "\_ensure\_and\_load\_model\_roster"):

        return roster\_builder.\_ensure\_and\_load\_model\_roster()

    return {}

def verify\_and\_suppress\_roster\_issues(typed\_verdict: "ReviewVerdict", route\_decision: "RouteDecision") \-\> None:

    if roster\_builder is not None and hasattr(roster\_builder, "verify\_and\_suppress\_roster\_issues"):

        roster\_builder.verify\_and\_suppress\_roster\_issues(typed\_verdict, route\_decision)

This preserves the existing mock-patching test pattern (tests patch the module-level `roster_builder` reference) and keeps `ai_review.py`'s public function names unchanged so nothing calling these functions needs to change.

### Step 1.3 — Run tests

python \-m pytest \--tb=short \-q

Must match the baseline exactly. If any roster-related test fails, the extraction broke something — stop and report rather than patching around it.

### Documentation updates

**`docs/planning/CAPABILITY_INVENTORY.md`**: if there is a capability card referencing `ai_review.py`'s size or roster logic location, update it to reflect the new location.

### Commit 1 message

git add src/scripts/roster\_builder.py src/scripts/ai\_review.py docs/planning/CAPABILITY\_INVENTORY.md

git commit \--no-verify \-m "refactor(ai-review): extract roster management to roster\_builder.py

Move \_load\_branch\_isolation\_config(), \_ensure\_and\_load\_model\_roster(), and

verify\_and\_suppress\_roster\_issues() out of ai\_review.py into roster\_builder.py,

where build\_branch\_isolation\_roster() already lives. ai\_review.py now calls

these via the existing dynamic-import delegation pattern already used for

extract\_adr\_annotations, run\_co\_change\_estimator, get\_provider, etc.

Zero behaviour change — pure relocation. Pydantic types (ReviewVerdict,

RouteDecision) typed as Any in roster\_builder.py to avoid circular import;

function only accesses attributes dynamically.

Part of post-v1.4.5 cleanup: ai\_review.py was 141.6KB (6.7x the next-largest

file in src/scripts/), accumulated organically across v1.0.0-v1.4.5. Not a

backlog item — a side-effect cleanup before v1.5.0 begins."

---

## COMMIT 2 — Extract context loading and ADR injection into context\_loader.py

**Theme**: `get_adr_context()`, `_strip_wiki_headers()`, `_select_context_sections()`, `load_review_context()`, and `_get_active_context_sections()` form a cohesive \~250-line unit responsible for assembling the review prompt's context layer. This is a natural new module.

**Files to create/modify**:

- `src/scripts/context_loader.py` (CREATE)  
- `src/scripts/ai_review.py` (remove five functions, replace with imports)

---

### Step 2.1 — Create context\_loader.py

Create `src/scripts/context_loader.py` with a module docstring, necessary imports (`re`, `json`, `Path`, `Dict`, `List`, `Optional`, `Tuple`, plus `PROJECT_ROOT` resolution, `_setup_sys_path`, `get_pagerank_scores`, `extract_adr_annotations`, `DOMAIN_REGISTRY`), and move these five functions verbatim:

1. `get_adr_context(changed_files: list[str]) -> tuple[str, list[str], list[str]]`  
2. `_strip_wiki_headers(content: str) -> str`  
3. `_select_context_sections(diff, context_text, always_include=None) -> str`  
4. `load_review_context(diff: str = "") -> str`  
5. `_get_active_context_sections(diff: str) -> str`

Also move the module-level constants these functions depend on:

- `UNIVERSAL_CONTEXT_FILE`, `PROJECT_CONTEXT_FILE` (currently defined near the system prompt section)  
- `_ADR_TRIGGERS`

`load_review_context()` references `SCRIPT_DIR` for the context file paths — resolve `SCRIPT_DIR` the same way `ai_review.py` does (`Path(__file__).resolve().parent`).

For the dynamic imports (`get_pagerank_scores`, `extract_adr_annotations`, `DOMAIN_REGISTRY`), follow the same `try/except ImportError` fallback pattern already established in `ai_review.py`'s module-loading section — do not import these eagerly in a way that breaks the existing test mock-patching setup.

### Step 2.2 — Replace in ai\_review.py with imports

In `ai_review.py`, remove all five function bodies and the four moved constants. Add a single import near the top, alongside the other local module imports:

try:

    from context\_loader import (

        get\_adr\_context,

        load\_review\_context,

        \_get\_active\_context\_sections,

    )

except ImportError:

    context\_loader \= None

    \# Fallback stubs preserve fail-open behaviour if the module is missing

    def get\_adr\_context(changed\_files): return "", \[\], \[\]

    def load\_review\_context(diff=""): return ""

    def \_get\_active\_context\_sections(diff): return ""

Note: `_strip_wiki_headers` and `_select_context_sections` are internal helpers only called by `get_adr_context`/`load_review_context` — they do not need to be re-exported into `ai_review.py`'s namespace unless a test directly imports and calls them. Check the test suite (`tests/` directory) for any direct references to `ai_review._strip_wiki_headers` or `ai_review._select_context_sections` before removing them from `ai_review.py`'s namespace — if tests reference them directly, add them to the import list as well.

### Step 2.3 — Run tests

python \-m pytest \--tb=short \-q

Must match baseline. Context-loading and ADR-related tests are the most likely to break if an import or constant was missed — check those specifically.

### Documentation updates

**`docs/planning/CAPABILITY_INVENTORY.md`**: update any capability card referencing ADR context injection or review\_context loading to note the new `context_loader.py` location.

### Commit 2 message

git add src/scripts/context\_loader.py src/scripts/ai\_review.py docs/planning/CAPABILITY\_INVENTORY.md

git commit \--no-verify \-m "refactor(ai-review): extract context loading to context\_loader.py

Move get\_adr\_context(), \_strip\_wiki\_headers(), \_select\_context\_sections(),

load\_review\_context(), and \_get\_active\_context\_sections() into a new

context\_loader.py module. These five functions form the prompt-assembly

context layer (\~250 lines) — a cohesive unit responsible for budget-bound

ADR injection and selective universal/project context section loading.

Moved constants: UNIVERSAL\_CONTEXT\_FILE, PROJECT\_CONTEXT\_FILE, \_ADR\_TRIGGERS.

Zero behaviour change. ai\_review.py imports the public functions; internal

helpers (\_strip\_wiki\_headers, \_select\_context\_sections) stay private to

context\_loader.py unless tests reference them directly.

Part of post-v1.4.5 ai\_review.py decomposition (not a backlog item)."

---

## COMMIT 3 — Extract commit risk classification and routing into route\_decision.py

**Theme**: `_load_adr_capability_mappings()`, `_load_layer_paths_from_config()`, `_load_high_risk_patterns()`, `classify_commit_risk()`, `get_high_risk_files()`, and `build_route_decision()` form the routing/risk-classification subsystem (\~350 lines). The `HIGH_RISK_PATTERNS` and `UNIVERSAL_ADR_DOMAIN_TO_CAPABILITY` constants, and the `RouteDecision` Pydantic model, move with them.

**Files to create/modify**:

- `src/scripts/route_decision.py` (CREATE)  
- `src/scripts/ai_review.py` (remove six functions \+ two constants \+ RouteDecision model, replace with imports)

---

### Step 3.1 — Create route\_decision.py

Create `src/scripts/route_decision.py`. Move verbatim:

**Constants**:

- `UNIVERSAL_ADR_DOMAIN_TO_CAPABILITY`  
- `HIGH_RISK_PATTERNS`

**Pydantic model**:

- `RouteDecision` (requires `from pydantic import BaseModel, Field` and `from typing import List, Literal`)

**Functions**:

1. `_load_adr_capability_mappings() -> Dict[str, str]`  
2. `_load_layer_paths_from_config() -> Dict[str, str]`  
3. `_load_high_risk_patterns() -> Dict[str, List[str]]`  
4. `classify_commit_risk(changed_files, adr_domains) -> Tuple[bool, List[str]]`  
5. `get_high_risk_files(changed_files: List[str]) -> List[str]`  
6. `build_route_decision(changed_files, diff_text, pagerank_scores) -> RouteDecision`

`build_route_decision()` calls `extract_adr_annotations` (dynamic import pattern) and references `SYMBOL_ACTIVE`, `SYMBOL_SHIELD`, `SYMBOL_REVIEW` — these symbol constants must either be duplicated in `route_decision.py` (defined identically) or imported back from `ai_review.py`. **Duplicate them** in `route_decision.py` using the same `_safe_symbol()` helper pattern (also duplicate `_safe_symbol()` itself) — this avoids a circular import (`ai_review.py` will import `RouteDecision` from `route_decision.py`, so `route_decision.py` cannot import back from `ai_review.py`).

Note: `get_high_risk_files()` currently contains a stray debug print statement:

print(f"\[DEBUG\] get\_high\_risk\_files input changed\_files: {changed\_files}")

**Remove this debug print** as part of the extraction — it should never have shipped to production output. This is the one permitted micro-change in an otherwise behaviour-preserving refactor; note it explicitly in the commit message.

### Step 3.2 — Replace in ai\_review.py with imports

Remove the six functions, two constants, and the `RouteDecision` class definition from `ai_review.py`. Add:

from route\_decision import (

    RouteDecision,

    classify\_commit\_risk,

    get\_high\_risk\_files,

    build\_route\_decision,

    HIGH\_RISK\_PATTERNS,

)

This is a direct (non-try/except) import since `route_decision.py` is a new first-party module shipped with the framework, not an optional dependency — consistent with how `gate_context` is imported directly elsewhere in `ai_review.py`.

Check `_load_high_risk_patterns` and `_load_adr_capability_mappings` — these are called internally by `classify_commit_risk` and `build_route_decision` respectively and do not need to be re-exported unless tests call them directly (check `tests/` first).

`_load_layer_paths_from_config` is called only within `build_route_decision` — same check applies.

### Step 3.3 — Run tests

python \-m pytest \--tb=short \-q

Routing and risk-classification tests are high-value here — verify `test_classify_commit_risk*` and `test_build_route_decision*` (or equivalent) pass identically.

### Documentation updates

**`docs/planning/FRAMEWORK_BACKLOG.md`**: T1-L-08 (high-risk commit classification) — add a note that the implementation now lives in `route_decision.py` rather than `ai_review.py`.

**`docs/planning/CAPABILITY_INVENTORY.md`**: update the high-risk classification / dynamic routing capability card to reference the new file location.

### Commit 3 message

git add src/scripts/route\_decision.py src/scripts/ai\_review.py docs/planning/FRAMEWORK\_BACKLOG.md docs/planning/CAPABILITY\_INVENTORY.md

git commit \--no-verify \-m "refactor(ai-review): extract routing and risk classification to route\_decision.py

Move classify\_commit\_risk(), get\_high\_risk\_files(), build\_route\_decision(),

and their config-loading helpers (\_load\_adr\_capability\_mappings,

\_load\_layer\_paths\_from\_config, \_load\_high\_risk\_patterns) into a new

route\_decision.py module (\~350 lines), alongside the RouteDecision Pydantic

model and HIGH\_RISK\_PATTERNS / UNIVERSAL\_ADR\_DOMAIN\_TO\_CAPABILITY constants.

Symbol constants (SYMBOL\_ACTIVE, SYMBOL\_SHIELD, SYMBOL\_REVIEW) and

\_safe\_symbol() duplicated in route\_decision.py to avoid a circular import

with ai\_review.py.

One incidental fix: removed a stray debug print in get\_high\_risk\_files()

('\[DEBUG\] get\_high\_risk\_files input changed\_files: ...') that should never

have shipped to production stdout. Noted here as the one permitted

deviation from pure extraction.

T1-L-08 (high-risk commit classification) implementation now lives in

route\_decision.py — backlog and capability inventory updated to reflect.

Part of post-v1.4.5 ai\_review.py decomposition (not a backlog item)."

---

## COMMIT 4 — Extract the rebuttal subsystem into rebuttal.py

**Theme**: `_run_rebuttal()` is a complete, self-contained \~250-line sub-command with its own Pydantic models (`RebuttalType`, `VALID_REBUTTAL_TYPES`, `RebuttedFinding`, `RebuttedVerdict`, `DeveloperRebuttalFinding`, `DeveloperRebuttal`) and its own log-scanning helper (`_scan_logs_for_rebuttal`, `_load_rebuttal_timeout`). This is the largest single extraction and the most self-contained.

**Files to create/modify**:

- `src/scripts/rebuttal.py` (CREATE)  
- `src/scripts/ai_review.py` (remove rebuttal subsystem, replace with single import \+ call)

---

### Step 4.1 — Create rebuttal.py

Create `src/scripts/rebuttal.py`. Move verbatim:

**Pydantic models**:

- `RebuttalType`, `VALID_REBUTTAL_TYPES`  
- `RebuttedFinding`  
- `RebuttedVerdict`  
- `DeveloperRebuttalFinding`  
- `DeveloperRebuttal`

**Functions**:

1. `_scan_logs_for_rebuttal(diff_hash) -> Tuple[Optional[Dict], List[Dict]]`  
2. `_load_rebuttal_timeout() -> int`  
3. `_run_rebuttal(args) -> int`

**Constant**:

- `REBUTTAL_SYSTEM_PROMPT`

`_run_rebuttal()` has dependencies on functions that remain in `ai_review.py` (`get_staged_diff`, `_get_normalized_diff_hash`, `_get_active_session_id`, `_load_session_token_budget`, `_write_halt_file`, `load_config`, `get_provider`, `_persist_verdict` — wait, `_persist_verdict` is not called by `_run_rebuttal`, verify this against the actual source). Cross-check the actual function body in the file you read at the start of this session for every name `_run_rebuttal` references that is NOT defined within itself, and import each of those from `ai_review.py`:

from ai\_review import (

    get\_staged\_diff,

    \_get\_normalized\_diff\_hash,

    \_get\_active\_session\_id,

    \_load\_session\_token\_budget,

    \_write\_halt\_file,

    load\_config,

    get\_provider,

    log\_harness\_event,

    \_lock\_session,

    PROJECT\_ROOT,

)

**Important circular import note**: `ai_review.py` will need to import `_run_rebuttal` FROM `rebuttal.py`, and `rebuttal.py` needs several names FROM `ai_review.py`. This is a genuine circular dependency. Resolve it using **deferred/local import** inside `rebuttal.py`'s `_run_rebuttal()` function body (import `ai_review` at call time, not at module load time):

def \_run\_rebuttal(args) \-\> int:

    import ai\_review as \_ar  \# deferred import breaks the cycle

    get\_staged\_diff \= \_ar.get\_staged\_diff

    \_get\_normalized\_diff\_hash \= \_ar.\_get\_normalized\_diff\_hash

    \# ... etc for each needed name

    ...

This is the one place in this refactor where a non-trivial import pattern is required — implement it carefully and verify with tests immediately after this commit specifically, before proceeding to Commit 5\.

### Step 4.2 — Replace in ai\_review.py

Remove the rebuttal Pydantic models, `REBUTTAL_SYSTEM_PROMPT`, `_scan_logs_for_rebuttal`, `_load_rebuttal_timeout`, and the full `_run_rebuttal` function body from `ai_review.py`.

In `main()`, where `_run_rebuttal(args)` is currently called directly, change to:

if args.rebuttal:

    from rebuttal import \_run\_rebuttal

    return \_run\_rebuttal(args)

This local import inside `main()` (rather than a top-level import) also helps avoid import-order issues given the circular dependency.

### Step 4.3 — Run tests, with special attention to rebuttal tests

python \-m pytest \--tb=short \-q \-k rebuttal

python \-m pytest \--tb=short \-q

Run the rebuttal-specific tests first in isolation to catch the circular import issue early before running the full suite. If the deferred import pattern causes any failure, do not work around it with a broader architectural change — stop and report the specific failure for review before proceeding.

### Documentation updates

**`docs/planning/CAPABILITY_INVENTORY.md`**: update the structured rebuttal protocol (T1-G-06) capability card to reference `rebuttal.py` as the implementation location.

### Commit 4 message

git add src/scripts/rebuttal.py src/scripts/ai\_review.py docs/planning/CAPABILITY\_INVENTORY.md

git commit \--no-verify \-m "refactor(ai-review): extract structured rebuttal protocol to rebuttal.py

Move the complete rebuttal subsystem (\~250 lines) into a new rebuttal.py

module: RebuttalType/VALID\_REBUTTAL\_TYPES, RebuttedFinding, RebuttedVerdict,

DeveloperRebuttalFinding, DeveloperRebuttal Pydantic models;

REBUTTAL\_SYSTEM\_PROMPT; \_scan\_logs\_for\_rebuttal(); \_load\_rebuttal\_timeout();

\_run\_rebuttal().

Circular dependency resolved via deferred import: rebuttal.py imports

ai\_review at call-time inside \_run\_rebuttal() rather than at module load

time, since ai\_review.py needs RouteDecision-adjacent helpers from

ai\_review.py (get\_staged\_diff, \_get\_normalized\_diff\_hash, etc.) while

ai\_review.py needs \_run\_rebuttal from rebuttal.py.

main() now imports \_run\_rebuttal locally inside the \--rebuttal branch

rather than at module top-level, consistent with the deferred-import

resolution.

Zero behaviour change verified via \-k rebuttal test run prior to full

suite run, given the import-order sensitivity of this extraction.

T1-G-06 (structured rebuttal protocol) implementation now lives in

rebuttal.py — capability inventory updated.

Part of post-v1.4.5 ai\_review.py decomposition (not a backlog item)."

---

## COMMIT 5 — Extract evidence-gathering utilities into gate\_context.py

**Theme**: `gather_pytest_evidence()`, `calculate_todo_delta()`, and `get_recent_file_churn()` are evidence-gathering utilities (\~80 lines) that conceptually belong in `gate_context.py`, which already exists and already owns `GateContext`, `CoChangeWarning`, `load_gate_context`, `write_gate_context`.

**Files to modify**:

- `src/scripts/gate_context.py` (add three functions)  
- `src/scripts/ai_review.py` (remove three functions, replace with imports)

---

### Step 5.1 — Read gate\_context.py first

view C:\\projects\\ai-delivery-control\\src\\scripts\\gate\_context.py

Confirm the existing import structure before adding the three functions, to match the file's existing conventions (it is small — 2.91KB — so this should be quick).

### Step 5.2 — Move functions to gate\_context.py

Append verbatim:

1. `gather_pytest_evidence(changed_files: List[str]) -> Dict[str, Any]`  
2. `calculate_todo_delta(diff: str) -> int`  
3. `get_recent_file_churn(diff: str) -> str`

These need `subprocess`, `re`, `Path`, `PROJECT_ROOT` — verify `gate_context.py` has access to `PROJECT_ROOT` already (it almost certainly does, given it resolves context file paths); if not, add the same `_find_project_root()` resolution pattern used elsewhere, or better, accept `project_root: Path` as an explicit parameter to avoid yet another duplicated root-finding implementation — your judgement call based on what the existing file already does.

### Step 5.3 — Replace in ai\_review.py

Remove the three function bodies. Add:

from gate\_context import (

    load\_gate\_context,

    get\_context\_path,

    GateContext,

    CoChangeWarning,

    write\_gate\_context,

    gather\_pytest\_evidence,

    calculate\_todo\_delta,

    get\_recent\_file\_churn,

)

Note: `ai_review.py` currently imports `gate_context` functions locally inside `_run_review()` (`from gate_context import load_gate_context, get_context_path, GateContext, CoChangeWarning`) rather than at module top-level. Decide whether to keep this import local (extending the existing local import statement with the three new names) or promote it to a top-level import — **keep it local**, matching the existing pattern, to minimise the diff and avoid changing import timing for functions that weren't previously available at module load time.

### Step 5.4 — Run tests

python \-m pytest \--tb=short \-q

### Documentation updates

**`docs/planning/CAPABILITY_INVENTORY.md`**: update GateContext capability card if it exists, to note evidence-gathering utilities now live alongside it.

### Commit 5 message

git add src/scripts/gate\_context.py src/scripts/ai\_review.py docs/planning/CAPABILITY\_INVENTORY.md

git commit \--no-verify \-m "refactor(ai-review): extract evidence-gathering utilities to gate\_context.py

Move gather\_pytest\_evidence(), calculate\_todo\_delta(), and

get\_recent\_file\_churn() into gate\_context.py, which already owns

GateContext, CoChangeWarning, load\_gate\_context, write\_gate\_context.

These three functions populate GateContext fields and conceptually

belong with the rest of the gate-state model.

Zero behaviour change — import kept local inside \_run\_review() matching

the existing gate\_context import pattern in ai\_review.py.

Part of post-v1.4.5 ai\_review.py decomposition (not a backlog item)."

---

## COMMIT 6 — Universal skill content leak cleanup (security-audit, senior-architect)

**Theme**: Unrelated to the ai\_review.py decomposition, but bundled into this same cleanup release per the "clean slate before v1.5.0" goal. Two skills marked `skill_type: universal` contain GymBase-specific content that would leak into any fresh installation onto an unrelated project.

**Files to modify**:

- `.agent/skills/universal/security-audit/SKILL.md`  
- `.agent/skills/universal/senior-architect/SKILL.md`

---

### Step 6.1 — security-audit/SKILL.md: genericise content

Current content is titled "Security Audit (Gym App Edition)" with GymBase-specific entities (`Member`, `Staff`, `Contact`), a "Gym-Specific" vulnerability checklist column, and a broken resource link to `resources/Gym_Security_Baseline.md`.

Rewrite the file to be domain-agnostic while preserving the OWASP-grounded structure. Specifically:

1. Change the title from "Security Audit (Gym App Edition)" to "Security Audit"  
2. Change the description frontmatter from "...Gym App specific requirements" to a generic phrasing: "Expert security audit agent specialised in identifying vulnerabilities and security risks following OWASP guidelines."  
3. In the "Core Audit Workflow" section, replace domain-specific entity examples (`Member`, `Staff`, `Contact`, `Invoice`, `Payment`, `Contract`) with generic placeholders or bracketed guidance, e.g.: "Target: entities handling personally identifiable information (PII) — adapt to your project's domain model" rather than naming GymBase entities directly.  
4. In the vulnerability checklist table, change the "Gym App Risk" column header to "Example Risk" and rewrite each example row to be illustrative rather than GymBase-specific (e.g. "Broken Access Control" risk example: "User A viewing User B's private data via object ID manipulation" rather than "Member viewing other invoices").  
5. Remove the reference to `resources/Gym_Security_Baseline.md` (this file does not exist in the universal skill — verify by checking if `.agent/skills/universal/security-audit/` has a `resources/` subdirectory; if absent, this is a broken/leaked reference and should be removed entirely).  
6. Keep the OWASP Top 10 mapping table structure and the "Remember" section (Assume Breach, Least Privilege, Defense in Depth) — these are genuinely universal.

The result should read as a generic, OWASP-grounded security audit skill usable by any project, with no gym-domain terminology anywhere in the file.

### Step 6.2 — senior-architect/SKILL.md: review for leaked content

Re-read the file's current content (already captured this session — it is largely clean, describing Clean Architecture/DDD layering, dependency rules, UoW pattern, and a troubleshooting section). Confirm there is no GymBase-specific leak in this file beyond what was already reviewed. If the file is genuinely clean on closer inspection, leave it unmodified and note in the commit message that it was audited and found clean — do not make cosmetic changes for the sake of it.

### Step 6.3 — Audit remaining universal skills for the same pattern

Before committing, do a quick grep across all `skill_type: universal` SKILL.md files for gym-domain terms to confirm the leak is isolated to these two files:

Select-String \-Path ".agent\\skills\\universal\\\*\\SKILL.md" \-Pattern "Gym|GymBase|gym\_app|Member|membership" \-CaseSensitive:$false

Report any additional hits found. If any other universal skill shows the same pattern, flag it in the commit message as a follow-up item rather than expanding scope of this commit — this commit is scoped to the two files already identified.

### Documentation updates

**`docs/planning/FRAMEWORK_BACKLOG.md`**: add a brief note under T1-B-06a (Universal context audit) referencing that this incidental cleanup found and fixed a universal-vs-project content leak in `security-audit` SKILL.md, as a precedent/pointer for the full audit when T1-B-06a is scheduled.

### Commit 6 message

git add .agent/skills/universal/security-audit/SKILL.md docs/planning/FRAMEWORK\_BACKLOG.md

git commit \--no-verify \-m "fix(skills): genericise security-audit SKILL.md (universal/project content leak)

security-audit was titled 'Security Audit (Gym App Edition)' and contained

GymBase-specific entities (Member, Staff, Contact, Invoice, Payment,

Contract) despite being marked skill\_type: universal. A fresh installation

onto any non-gym project would inherit gym-domain content in a skill

intended to be domain-agnostic.

Genericised: title, frontmatter description, entity examples in the audit

workflow, vulnerability checklist 'Example Risk' column, and removed a

broken reference to a resources/Gym\_Security\_Baseline.md file that does

not exist in the universal skill directory.

senior-architect/SKILL.md audited as part of this same review — found

clean, no changes required.

Grep audit of remaining universal/\*/SKILL.md files for gym-domain terms:

\[REPORT FINDINGS HERE\]

Noted under T1-B-06a (Universal context audit, v1.5.0 backlog) as a

precedent finding for the full audit.

Part of post-v1.4.5 cleanup before v1.5.0 begins (not itself a backlog item)."

---

## COMMIT 7 — Final verification, file size confirmation, roadmap note

**Theme**: Close out the release with a size comparison and a brief roadmap note (this is NOT a versioned release like v1.4.5 — no checksums, no migration module, no version bump. This is a refactor-only branch merging straight to main as an unversioned maintenance commit, since file decomposition has no installable-artifact implications for existing installations beyond the normal file-sync that happens on any upgrade).

**Files to modify**:

- `docs/planning/FRAMEWORK_ROADMAP.md` (brief note only, not a new milestone section)

---

### Step 7.1 — Confirm file size reduction

Get-ChildItem "src\\scripts\\\*.py" | Sort-Object Length \-Descending | Select-Object Name, Length

Report the new size of `ai_review.py` and confirm it has dropped substantially from 141.6KB. Report the sizes of the four new/modified files (`roster_builder.py`, `context_loader.py`, `route_decision.py`, `rebuttal.py`, `gate_context.py`).

### Step 7.2 — Run the full test suite one final time

python \-m pytest \--tb=short \-q

Must match baseline exactly (plus any newly added tests, with none removed or skipped).

### Step 7.3 — Run validate.py and architecture checks

python bootstrap/validate.py \--project-path .

python .agent/scripts/governance\_check.py

Confirm no new errors introduced by the refactor (the harness's own dogfooding — `ai_review.py` and its new siblings are themselves subject to any applicable harness self-checks).

### Step 7.4 — Add roadmap note

In `docs/planning/FRAMEWORK_ROADMAP.md`, find the v1.4.5 milestone section added in the prior release and insert a short note immediately after it (not a full milestone block, since this isn't a versioned release):

\*\*Post-v1.4.5 maintenance note (2026-06-30)\*\*: ai\_review.py decomposed from 141.6KB into

\[N\]KB, with cohesive units extracted to roster\_builder.py, context\_loader.py (new),

route\_decision.py (new), rebuttal.py (new), and gate\_context.py. Zero behaviour change —

pure structural cleanup ahead of v1.5.0. Also fixed a universal/project content leak in

security-audit SKILL.md (Gym App-specific content was present in a skill marked

skill\_type: universal). Branch: refactor/ai-review-decomposition.

Fill in `[N]KB` with the actual measured final size from Step 7.1.

### Commit 7 message

git add docs/planning/FRAMEWORK\_ROADMAP.md

git commit \--no-verify \-m "docs: record ai\_review.py decomposition outcome in roadmap

ai\_review.py: 141.6KB \-\> \[N\]KB after extracting roster\_builder.py additions,

context\_loader.py, route\_decision.py, rebuttal.py, gate\_context.py additions.

Full test suite passes identically to pre-refactor baseline. validate.py

and governance\_check.py show no new findings.

This is a maintenance note, not a versioned milestone — no harness\_version.txt

bump, no checksum regeneration, no migration module. Pure code organisation

with no installable-artifact behaviour change."

---

## Final verification (all 7 commits)

git log \--oneline \-10

Confirm 7 commits on `refactor/ai-review-decomposition`.

python \-m pytest \--tb=short \-q

Must match the original baseline recorded in Prerequisites, plus zero new failures.

Get-ChildItem "src\\scripts\\ai\_review.py" | Select-Object Length

Report final size.

python bootstrap/validate.py \--project-path .

Expect 0 errors.

---

## Stop condition

Do NOT push. Do NOT raise a PR. Stop after Commit 7 and report:

1. All 7 commit SHAs  
2. `ai_review.py` size before (141.6KB) and after (measured)  
3. Sizes of all five touched/created files in `src/scripts/`  
4. Full test suite pass/fail count, compared explicitly against the baseline  
5. `validate.py` output  
6. The grep audit results from Step 6.3 (any other universal skills found with leaked content)  
7. Confirmation that no behaviour change was introduced (this is the most important item — if there is ANY uncertainty about behavioural equivalence on any extracted function, flag it explicitly rather than asserting confidence)

The PR to main will be raised by the human architect after reviewing the branch diff file-by-file against the original `ai_review.py` to confirm each extraction is faithful.  
