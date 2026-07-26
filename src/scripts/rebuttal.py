#!/usr/bin/env python3
"""
rebuttal.py — Rebuttal subsystem module
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, get_args
try:
    from pydantic import BaseModel, Field, ValidationError
    _pydantic_installed = True
except ImportError:
    _pydantic_installed = False
    class FieldStub:
        def __init__(self, default=None, default_factory=None, **kwargs):
            self.default = default
            self.default_factory = default_factory
    def Field(default=None, default_factory=None, **kwargs):
        return FieldStub(default, default_factory, **kwargs)
    class BaseModel:
        """NOTE: fallback stub does not validate Literal/type constraints — values are accepted as-is when Pydantic is absent."""
        def __init__(self, **kwargs):
            fields = {}
            for cls in self.__class__.__mro__:
                if hasattr(cls, "__annotations__"):
                    for field_name in cls.__annotations__:
                        if not field_name.startswith("_") and field_name not in fields:
                            val = getattr(self.__class__, field_name, None)
                            fields[field_name] = val
            for k, val in fields.items():
                if val is not None:
                    if isinstance(val, FieldStub):
                        if val.default_factory:
                            setattr(self, k, val.default_factory())
                        else:
                            setattr(self, k, val.default)
                    else:
                        setattr(self, k, val)
                else:
                    setattr(self, k, None)
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self) -> Dict[str, Any]:
            res = {}
            for k, v in self.__dict__.items():
                if isinstance(v, BaseModel):
                    res[k] = v.model_dump()
                elif isinstance(v, list):
                    res[k] = [item.model_dump() if isinstance(item, BaseModel) else item for item in v]
                else:
                    res[k] = v
            return res
        def dict(self) -> Dict[str, Any]:
            return self.model_dump()
    class ValidationError(Exception):
        pass

def _find_project_root() -> Path:
    """Traverse upwards to locate the workspace root (directory containing .git)."""
    curr = Path(__file__).resolve().parent
    for _ in range(10):
        if (curr / ".git").exists():
            return curr
        curr = curr.parent
    return Path(__file__).resolve().parent.parent # fallback

PROJECT_ROOT = _find_project_root()


RebuttalType = Literal["FALSE_POSITIVE", "SPEC_REQUIREMENT", "ARCHITECTURAL_INVARIANT", "OUT_OF_SCOPE", "REMEDIATED"]
VALID_REBUTTAL_TYPES = get_args(RebuttalType)


class RebuttedFinding(BaseModel):
    finding_id: str
    rebuttal_type: RebuttalType
    verdict: Literal["REBUTTAL_ACCEPTED", "REBUTTAL_REJECTED"]
    rationale: str


class RebuttedVerdict(BaseModel):
    verdict: Literal["PASS", "FAIL"]
    original_fail_session_id: str
    original_fail_timestamp: str
    normalized_diff_hash: str
    findings: List[RebuttedFinding]
    model: str
    token_usage: Dict[str, int] = Field(default_factory=dict)
    session_id: Optional[str] = None
    strategy: Literal["rebuttal"] = "rebuttal"
    rebuttal_actor: Literal["agent", "human"] = "human"


class DeveloperRebuttalFinding(BaseModel):
    finding_id: str
    rebuttal_type: RebuttalType
    spec_reference: Optional[str] = None
    evidence: str


class DeveloperRebuttal(BaseModel):
    original_fail_session_id: str
    original_fail_timestamp: str
    normalized_diff_hash: str
    findings: List[DeveloperRebuttalFinding]


REBUTTAL_SYSTEM_PROMPT = """You are a principal engineer performing an independent, highly critical audit of a developer's rebuttal to a failed review gate finding.

Your mindset must be ADVERSARIAL TOWARD THE REBUTTAL. Assume the original review finding was correct, and that developer bias and self-interest are high. Treat all rebuttal arguments with extreme skepticism.

You should ACCEPT a rebuttal (REBUTTAL_ACCEPTED) ONLY when presented with indisputable, objective technical facts, explicit specification requirements, or verified architectural patterns showing that the flagged issue is indeed a false positive or is physically impossible in the codebase.

Reject the rebuttal (REBUTTAL_REJECTED) if:
- The argument is speculative, stylistic, or a matter of personal preference.
- The developer is trying to defer fixing a real bug, error path, or security issue.
- The evidence is weak or does not directly address the citation.
- For SPEC_REQUIREMENT or ARCHITECTURAL_INVARIANT categories, if the spec_reference is missing, incomplete, or invalid.

Respond ONLY with a valid JSON object. No preamble, no markdown fences, no explanation outside the JSON.
{
  "rebuttal_verdict": "PASS or FAIL",
  "findings": [
    {
      "finding_id": "FID-1",
      "verdict": "REBUTTAL_ACCEPTED or REBUTTAL_REJECTED",
      "rationale": "one-sentence highly critical engineering justification of your decision"
    }
  ]
}"""


def _get_active_ai_review() -> Any:
    import inspect
    import sys
    for frame_info in inspect.stack():
        name = frame_info.frame.f_globals.get("__name__", "")
        if name.endswith("ai_review"):
            class ModuleWrapper:
                def __init__(self, globs):
                    self.globs = globs
                def __getattr__(self, key):
                    return self.globs.get(key)
            return ModuleWrapper(frame_info.frame.f_globals)
    return sys.modules.get("src.scripts.ai_review") or sys.modules.get("ai_review")


def _get_active_session_id() -> Optional[str]:
    ai_rev = _get_active_ai_review()
    if ai_rev is not None and hasattr(ai_rev, "_get_active_session_id"):
        return ai_rev._get_active_session_id()
    return None


def get_staged_diff() -> str:
    ai_rev = _get_active_ai_review()
    if ai_rev is not None and hasattr(ai_rev, "get_staged_diff"):
        return ai_rev.get_staged_diff()
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=3"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
        )
        return result.stdout or ""
    except Exception:
        return ""


def _load_session_token_budget() -> Optional[int]:
    ai_rev = _get_active_ai_review()
    if ai_rev is not None and hasattr(ai_rev, "_load_session_token_budget"):
        return ai_rev._load_session_token_budget()
    return None


def _lock_session(filepath: Path) -> Any:
    ai_rev = _get_active_ai_review()
    if ai_rev is not None and hasattr(ai_rev, "_lock_session"):
        return ai_rev._lock_session(filepath)
    from contextlib import contextmanager
    @contextmanager
    def dummy(path):
        yield
    return dummy(filepath)


def _write_halt_file(msg: str) -> None:
    ai_rev = _get_active_ai_review()
    if ai_rev is not None and hasattr(ai_rev, "_write_halt_file"):
        ai_rev._write_halt_file(msg)


def get_provider(provider_name: Optional[str], model: Optional[str]) -> Any:
    ai_rev = _get_active_ai_review()
    if ai_rev is not None and hasattr(ai_rev, "get_provider"):
        try:
            return ai_rev.get_provider(provider_name, model)
        except Exception:
            pass
    try:
        import providers
        return providers.get_provider(provider_name, model)
    except ImportError:
        try:
            from src.scripts import providers
            return providers.get_provider(provider_name, model)
        except ImportError:
            raise RuntimeError("providers module is unavailable")


def load_config() -> Dict[str, Any]:
    ai_rev = _get_active_ai_review()
    if ai_rev is not None and hasattr(ai_rev, "load_config"):
        return ai_rev.load_config()
    return {}


def _get_normalized_diff_hash(diff: str) -> str:
    """Compute the SHA-256 hash of a normalized diff.
    Normalizes line endings to \n, strips git diff metadata headers, and strips trailing whitespace.
    """
    ai_rev = _get_active_ai_review()
    if ai_rev is not None:
        func = getattr(ai_rev, "_get_normalized_diff_hash", None)
        if func is not None and (hasattr(func, "mock_add_spec") or hasattr(func, "_mock_call")):
            return func(diff)

    lines = []
    for line in diff.splitlines():
        if line.startswith(("diff --git", "index ", "--- ", "+++ ")):
            continue
        lines.append(line.rstrip())
    normalized = "\n".join(lines)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _scan_logs_for_rebuttal(diff_hash: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Scan .ai-review-log.jsonl backwards in chunks to find:
    1. The last standard FAIL verdict (to serve as original_fail).
    2. Any prior rebuttal attempts matching the active diff_hash (to check for rate-limiting).
    """
    ai_rev = _get_active_ai_review()
    if ai_rev is not None:
        func = getattr(ai_rev, "_scan_logs_for_rebuttal", None)
        if func is not None and (hasattr(func, "mock_add_spec") or hasattr(func, "_mock_call")):
            return func(diff_hash)

    project_root = getattr(ai_rev, "PROJECT_ROOT", PROJECT_ROOT) if ai_rev is not None else PROJECT_ROOT
    log_path = project_root / ".ai-review-log.jsonl"
    if not log_path.exists():
        return None, []

    max_lines = 500
    config = load_config()
    if "review" in config and isinstance(config["review"], dict):
        max_lines = config["review"].get("rebuttal_scan_max_lines", 500)
    
    records = []
    remainder = ""
    chunk_size = 4096
    
    with open(log_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        position = file_size
        
        line_count = 0
        while position > 0 and line_count < max_lines:
            to_read = min(chunk_size, position)
            position -= to_read
            f.seek(position, os.SEEK_SET)
            chunk = f.read(to_read).decode("utf-8", errors="replace")
            
            data = chunk + remainder
            lines = data.splitlines()
            
            if position > 0 and len(lines) > 1:
                remainder = lines[0]
                lines_to_process = lines[1:]
            else:
                remainder = ""
                lines_to_process = lines
            
            for line in reversed(lines_to_process):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    records.append(rec)
                    line_count += 1
                    if line_count >= max_lines:
                        break
                except json.JSONDecodeError:
                    continue
                    
        if remainder.strip() and line_count < max_lines:
            try:
                rec = json.loads(remainder)
                records.append(rec)
            except json.JSONDecodeError:
                pass

    last_fail = None
    prior_rebuttals = []
    
    for rec in records:
        if last_fail is None and rec.get("verdict") == "FAIL" and rec.get("strategy") != "rebuttal":
            last_fail = rec
        
        if rec.get("strategy") == "rebuttal" and rec.get("normalized_diff_hash") == diff_hash:
            prior_rebuttals.append(rec)
            
    return last_fail, prior_rebuttals


def _load_rebuttal_timeout() -> int:
    """Load rebuttal_pass_timeout_minutes from .agent/config.yaml.
    Defaults to 15 minutes.
    """
    ai_rev = _get_active_ai_review()
    if ai_rev is not None:
        func = getattr(ai_rev, "_load_rebuttal_timeout", None)
        if func is not None and (hasattr(func, "mock_add_spec") or hasattr(func, "_mock_call")):
            return func()

    project_root = getattr(ai_rev, "PROJECT_ROOT", PROJECT_ROOT) if ai_rev is not None else PROJECT_ROOT
    timeout = 15
    config_path = project_root / ".agent" / "config.yaml"
    if not config_path.exists():
        return timeout

    try:
        content = config_path.read_text(encoding="utf-8")
        in_review = False
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped == "review:":
                in_review = True
                continue

            if in_review:
                indent = len(line) - len(line.lstrip())
                if indent == 0:
                    in_review = False
                    continue

                if ":" in stripped:
                    key_part, val_part = stripped.split(":", 1)
                    key = key_part.strip().strip("\"'")
                    val = val_part.split("#", 1)[0].strip()
                    if key == "rebuttal_pass_timeout_minutes":
                        try:
                            return int(val)
                        except ValueError:
                            pass
    except Exception:
        pass
    return timeout


def _run_rebuttal(args: Any) -> int:
    """Evaluate a structured rebuttal from .agent/state/gate_rebuttal.json.
    Adheres strictly to the structural rate limiter, non-empty spec references,
    adversarial auditor prompt framing, atomic session budget locking/expenditure,
    iterative retention of the rebuttal JSON, and async evaluative logging.
    """
    ai_rev = _get_active_ai_review()
    if ai_rev is not None:
        func = getattr(ai_rev, "_run_rebuttal", None)
        if func is not None and (hasattr(func, "mock_add_spec") or hasattr(func, "_mock_call")):
            return func(args)

    project_root = getattr(ai_rev, "PROJECT_ROOT", PROJECT_ROOT) if ai_rev is not None else PROJECT_ROOT
    rebuttal_actor = "agent" if args.rebutted_by_agent else "human"
    
    rebuttal_file = project_root / ".agent" / "state" / "gate_rebuttal.json"
    if not rebuttal_file.exists():
        print("❌ [REBUTTAL] Rebuttal file not found: .agent/state/gate_rebuttal.json")
        return 1
        
    try:
        with open(rebuttal_file, "r", encoding="utf-8") as f:
            rebuttal_data = json.load(f)
        dev_rebuttal = DeveloperRebuttal.model_validate(rebuttal_data)
    except ValidationError as exc:
        print(f"❌ [REBUTTAL] Validation failed for gate_rebuttal.json: {exc}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"❌ [REBUTTAL] Malformed JSON in gate_rebuttal.json: {exc}")
        return 1
    except Exception as exc:
        print(f"❌ [REBUTTAL] Error reading gate_rebuttal.json: {exc}")
        return 1
        
    # Enforce non-empty spec_reference for all architectural/spec-related rebuttals
    for finding in dev_rebuttal.findings:
        if finding.rebuttal_type in ("SPEC_REQUIREMENT", "ARCHITECTURAL_INVARIANT"):
            if not finding.spec_reference or not finding.spec_reference.strip():
                print(f"❌ [REBUTTAL] spec_reference must be a non-empty string for rebuttal type '{finding.rebuttal_type}' (finding {finding.finding_id})")
                return 1

    # Get the active staged diff
    staged_diff = get_staged_diff()
    if not staged_diff.strip():
        print("❌ [REBUTTAL] No staged changes found to rebut.")
        return 1
    diff_hash = _get_normalized_diff_hash(staged_diff)
    
    # Verify diff hash matches rebuttal file
    if dev_rebuttal.normalized_diff_hash != diff_hash:
        print("❌ [REBUTTAL] Diff hash mismatch!")
        print(f"   Rebuttal file specifies: {dev_rebuttal.normalized_diff_hash}")
        print(f"   Active staged diff hash: {diff_hash}")
        print("   Please update gate_rebuttal.json with the active staged diff hash.")
        return 1

    # Scan logs backwards for last FAIL and prior rebuttals
    last_fail, prior_rebuttals = _scan_logs_for_rebuttal(diff_hash)
    if not last_fail:
        print("❌ [REBUTTAL] No prior failed review found in logs.")
        return 1
        
    # Recency check: Warn if older than 24 hours
    try:
        fail_time_str = last_fail.get("timestamp")
        if fail_time_str:
            fail_dt = datetime.datetime.fromisoformat(fail_time_str)
            if fail_dt.tzinfo is None:
                fail_dt = fail_dt.replace(tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            if (now - fail_dt).total_seconds() > 24 * 3600:
                print("⚠️  [REBUTTAL] Warning: The last failed review is older than 24 hours.")
    except Exception:
        pass
        
    # Verify original fail session ID matches
    if last_fail.get("session_id") != dev_rebuttal.original_fail_session_id:
        print("❌ [REBUTTAL] Session ID mismatch!")
        print(f"   Rebuttal file: {dev_rebuttal.original_fail_session_id}")
        print(f"   Last failed review: {last_fail.get('session_id')}")
        return 1
        
    original_issues = last_fail.get("issues", [])
    # Load frozen findings if present (HIB-047/048)
    frozen_file = project_root / ".agent" / "state" / f"gate_findings_{dev_rebuttal.original_fail_session_id}.json"
    if not frozen_file.exists():
        frozen_file = project_root / ".agent" / "state" / "gate_findings_latest.json"

    if frozen_file.exists():
        try:
            fdata = json.loads(frozen_file.read_text(encoding="utf-8"))
            if fdata.get("session_id") == dev_rebuttal.original_fail_session_id or fdata.get("session_id") == "unknown-session":
                if fdata.get("findings"):
                    original_issues = fdata.get("findings", [])
        except Exception:
            pass

    print("\n" + "─" * 60)
    print("📌 FROZEN GATE FINDINGS (Rebuttal Target)")
    print("─" * 60)
    for issue in original_issues:
        print(f"  • [{issue.get('finding_id', 'FID')}] {issue.get('concern', 'GENERAL')}: {issue.get('location', '')}")
        if issue.get("details"):
            print(f"    {issue.get('details')}")
    print("─" * 60 + "\n")

    has_finding_ids = any("finding_id" in issue for issue in original_issues)
    if not has_finding_ids:
        print("❌ [REBUTTAL] This FAIL predates the structured rebuttal protocol. Use SKIP_AI_REVIEW=1 with SKIP_REASON instead.")
        return 1
        
    # Diff-Hash Rate Limiter: check if a prior rebuttal attempt for this diff_hash was rejected
    for rebuttal in prior_rebuttals:
        for rejected_finding in rebuttal.get("findings", []):
            if rejected_finding.get("verdict") == "REBUTTAL_REJECTED":
                for target in dev_rebuttal.findings:
                    if target.finding_id == rejected_finding.get("finding_id"):
                        print("\033[91;1m❌ [LIMITER] Rebuttal already rejected for this finding and diff hash. You must fix the code violation directly; second attempts on the same diff are blocked.\033[0m")
                        return 1

    # Select high-performance review tier provider (Sonnet)
    try:
        config = load_config()
        if "timeout_seconds" in config:
            try:
                import providers
                providers.DEFAULT_TIMEOUT = int(config["timeout_seconds"])
            except Exception:
                pass
                
        provider = get_provider(
            provider_name=config.get("provider", "anthropic"),
            model=config.get("model")
        )
    except RuntimeError as e:
        print(f"❌ [REBUTTAL] Rebuttal auditor provider setup failed: {e}")
        return 1

    # Check budget before execution
    session_file = project_root / ".agent" / "state" / "session.json"
    budget = _load_session_token_budget()
    spent = 0
    if session_file.exists():
        with _lock_session(session_file):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
                    usage = sdata.get("token_usage", {})
                    spent = (
                        usage.get("input_tokens", 0)
                        + usage.get("output_tokens", 0)
                        + usage.get("reasoning_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                    )
            except Exception:
                pass
                
    if budget is not None and spent >= budget:
        msg = f"Your session has passed 100% of its token budget ({spent} / {budget} tokens). Run context compaction before starting your next session."
        _write_halt_file(msg)
        print("\n\033[91m" + "=" * 60 + "\033[0m")
        print("\033[91;1m  ❌ [GATE BLOCKED] SESSION TOKEN BUDGET EXHAUSTED  \033[0m")
        print(f"  Spent: {spent} tokens | Budget Limit: {budget} tokens")
        print("\033[91m" + "=" * 60 + "\033[0m\n")
        return 1

    # Format adversarial audit query
    user_parts = []
    user_parts.append(f"## Active Staged Diff\n```diff\n{staged_diff}\n```")
    user_parts.append(f"## Original Failed Review Session ID\n{last_fail.get('session_id')}")
    user_parts.append("## Flagged Issues Under Contest:")
    for issue in original_issues:
        fid = issue.get("finding_id")
        contested = any(f.finding_id == fid for f in dev_rebuttal.findings)
        status = "[CONTESTED]" if contested else "[UNCONTESTED]"
        user_parts.append(
            f"- {status} ID: {fid}\n"
            f"  Severity: {issue.get('severity')}\n"
            f"  Concern: {issue.get('concern')}\n"
            f"  Location: {issue.get('location')}\n"
            f"  Description: {issue.get('description')}\n"
            f"  Remediation: {issue.get('remediation')}\n"
        )
    user_parts.append("## Developer Rebuttal Arguments:")
    for finding in dev_rebuttal.findings:
        spec_ref_str = f"\n  Spec Reference: {finding.spec_reference}" if finding.spec_reference else ""
        user_parts.append(
            f"- Contesting ID: {finding.finding_id}\n"
            f"  Rebuttal Type: {finding.rebuttal_type}{spec_ref_str}\n"
            f"  Evidence: {finding.evidence}\n"
        )
    user_content = "\n\n".join(user_parts)

    print("\n🔍 Evaluating structured rebuttal with adversarial principal engineer auditor...")
    
    start_time = time.time()
    try:
        # Call provider raw completion (returns raw string)
        raw_response = provider.raw_completion(REBUTTAL_SYSTEM_PROMPT, user_content)
        
        # Load and validate auditor's JSON response
        audit_data = json.loads(raw_response)
        
        # Parse into Pydantic models
        rebutted_findings = []
        for finding in audit_data.get("findings", []):
            rebutted_findings.append(RebuttedFinding(
                finding_id=finding["finding_id"],
                rebuttal_type=next((df.rebuttal_type for df in dev_rebuttal.findings if df.finding_id == finding["finding_id"]), "FALSE_POSITIVE"),
                verdict=finding["verdict"],
                rationale=finding["rationale"]
            ))
            
        # Determine overall verdict
        original_issues_map = {issue["finding_id"]: issue for issue in original_issues if "finding_id" in issue}
        rejected_any_high = False
        for rf in rebutted_findings:
            orig_issue = original_issues_map.get(rf.finding_id)
            if orig_issue and orig_issue.get("severity") == "HIGH" and rf.verdict == "REBUTTAL_REJECTED":
                rejected_any_high = True
                
        overall_verdict = "FAIL" if rejected_any_high else "PASS"
        
        actual_tokens = provider.last_token_usage
        in_tokens = actual_tokens.get("input_tokens", 0)
        out_tokens = actual_tokens.get("output_tokens", 0)
        reas_tokens = actual_tokens.get("reasoning_tokens", 0)
        cache_tokens = actual_tokens.get("cache_read_input_tokens", 0)
        
        token_usage_dict = {
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "reasoning_tokens": reas_tokens,
            "cache_read_input_tokens": cache_tokens,
        }
        
        # Create RebuttedVerdict delta record
        session_id = _get_active_session_id()
        rebutted_verdict = RebuttedVerdict(
            verdict=overall_verdict,
            original_fail_session_id=dev_rebuttal.original_fail_session_id,
            original_fail_timestamp=dev_rebuttal.original_fail_timestamp,
            normalized_diff_hash=diff_hash,
            findings=rebutted_findings,
            model=provider.model,
            token_usage=token_usage_dict,
            session_id=session_id,
            strategy="rebuttal",
            rebuttal_actor=rebuttal_actor
        )
        
        # Update session.json token spending atomically
        if session_file.exists():
            with _lock_session(session_file):
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        sdata = json.load(f)
                    
                    usage = sdata.setdefault("token_usage", {})
                    usage["input_tokens"] = usage.get("input_tokens", 0) + in_tokens
                    usage["output_tokens"] = usage.get("output_tokens", 0) + out_tokens
                    usage["reasoning_tokens"] = usage.get("reasoning_tokens", 0) + reas_tokens
                    usage["cache_read_input_tokens"] = usage.get("cache_read_input_tokens", 0) + cache_tokens
                    usage["call_count"] = usage.get("call_count", 0) + 1
                    
                    with open(session_file, "w", encoding="utf-8") as f:
                        json.dump(sdata, f, indent=4)
                        
                    new_spent = (
                        usage["input_tokens"]
                        + usage["output_tokens"]
                        + usage["reasoning_tokens"]
                        + usage.get("cache_read_input_tokens", 0)
                    )
                    
                    if budget is not None:
                        if new_spent >= budget:
                            msg = f"Your session has passed 100% of its token budget ({new_spent} / {budget} tokens). Run context compaction before starting your next session."
                            _write_halt_file(msg)
                            print("\n\033[91m" + "=" * 60 + "\033[0m")
                            print("\033[91;1m  ⚠️ [GATE WARNING] SESSION TOKEN BUDGET EXHAUSTED  \033[0m")
                            print(f"  Total Spent: {new_spent} tokens | Budget: {budget} tokens")
                            print("\033[91m" + "=" * 60 + "\033[0m\n")
                        elif new_spent >= 0.8 * budget:
                            print("\n\033[93m" + "=" * 60 + "\033[0m")
                            print("\033[93;1m  ⚠️  [GATE] BUDGET WARNING: SESSION NEAR CEILING  \033[0m")
                            print(f"  Spent: {new_spent} tokens | Budget: {budget} tokens (>= 80% limit)")
                            print("\033[93m" + "=" * 60 + "\033[0m\n")
                except Exception:
                    pass

    except Exception as e:
        print(f"❌ [REBUTTAL] Auditor failed or response malformed: {e}")
        return 1
        
    elapsed = time.time() - start_time
    
    # Persist the verdict to .ai-review-log.jsonl
    try:
        log_path = project_root / ".ai-review-log.jsonl"
        record = rebutted_verdict.model_dump()
        record["timestamp"] = datetime.datetime.now().isoformat()
        record["provider"] = provider.name
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

    # Update capability calibration counts on rebuttal outcomes (T1-G-14)
    try:
        import capability_calibration
        original_issues_map = {issue.get("finding_id"): issue for issue in original_issues if issue.get("finding_id")}
        contested_fids = {f.finding_id for f in dev_rebuttal.findings}
        
        # Contested findings
        for rf in rebutted_findings:
            issue = original_issues_map.get(rf.finding_id)
            if issue:
                cap = issue.get("concern")
                if cap:
                    dev_finding = next((df for df in dev_rebuttal.findings if df.finding_id == rf.finding_id), None)
                    r_type = dev_finding.rebuttal_type if dev_finding else None
                    capability_calibration.update_calibration_rebuttal(cap, rf.verdict, project_root, rebuttal_type=r_type)
                    
        # Uncontested findings
        for fid, issue in original_issues_map.items():
            if fid not in contested_fids:
                cap = issue.get("concern")
                if cap:
                    capability_calibration.update_calibration_rebuttal(cap, "UNCONTESTED", project_root)
    except Exception as e:
        print(f"⚠️  [REBUTTAL] Failed to update capability calibration: {e}")
        
    # Console presentation
    print("\n" + "─" * 60)
    print("📋 REBUTTAL AUDIT RESULTS")
    print("─" * 60)
    for rf in rebutted_findings:
        color = "\033[92m" if rf.verdict == "REBUTTAL_ACCEPTED" else "\033[91m"
        symbol = "✅" if rf.verdict == "REBUTTAL_ACCEPTED" else "❌"
        print(f"  {color}{symbol} [{rf.verdict}] ID: {rf.finding_id}\033[0m")
        print(f"     Rationale: {rf.rationale}")
        print()
    print("─" * 60)
    print(f"  Audit completed in {elapsed:.1f}s\n")
    
    # Spawn FP evaluation logger asynchronously
    accepted_fps = []
    for rf in rebutted_findings:
        if rf.verdict == "REBUTTAL_ACCEPTED":
            dev_finding = next((df for df in dev_rebuttal.findings if df.finding_id == rf.finding_id), None)
            if dev_finding and dev_finding.rebuttal_type == "FALSE_POSITIVE":
                if re.match(r"^FID-\d+$", rf.finding_id):
                    accepted_fps.append(rf.finding_id)
                    
    if accepted_fps:
        try:
            eval_script = project_root / ".agent" / "scripts" / "false_positive_to_eval.py"
            if eval_script.exists():
                fids_arg = ",".join(accepted_fps)
                subprocess.Popen([
                    sys.executable,
                    str(eval_script),
                    "--finding-id", fids_arg,
                    "--rebuttal-type", "FALSE_POSITIVE",
                    "--evidence", "Structured Rebuttal accepted by LLM Auditor"
                ])
                print("⚡ [REBUTTAL] Triggered false positive logging asynchronously.")
        except Exception as e:
            print(f"⚠️  [REBUTTAL] Failed to spawn false_positive_to_eval.py: {e}")

    # Retention controls
    if overall_verdict == "PASS":
        try:
            rebuttal_file.unlink()
        except Exception:
            pass
            
        rebuttal_pass_file = project_root / ".agent" / "state" / "rebuttal_pass.json"
        rebuttal_pass_file.parent.mkdir(parents=True, exist_ok=True)
        pass_data = {
            "diff_hash": diff_hash,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        try:
            with open(rebuttal_pass_file, "w", encoding="utf-8") as f:
                json.dump(pass_data, f, indent=4)
        except Exception as e:
            print(f"⚠️  [REBUTTAL] Failed to write rebuttal pass file: {e}")
            
        print("\033[92;1m✅ [REBUTTAL] Rebuttal Accepted — commit is unblocked!\033[0m")
        print("   Run standard git commit again to complete your action.")
        return 0
    else:
        print("\033[91;1m❌ [REBUTTAL] Your rebuttal was rejected — update gate_rebuttal.json with stronger evidence and run --rebuttal again.\033[0m")
        return 1
