import pytest
from pathlib import Path
import tempfile
import shutil
import json
from src.scripts.gate_context import (
    GateContext,
    ArchViolation,
    CoChangeWarning,
    load_gate_context,
    write_gate_context,
    get_context_path,
    calculate_todo_delta,
    gather_pytest_evidence
)
from src.scripts.ai_review import (
    build_deterministic_findings_section,
)

def test_gate_context_defaults():
    ctx = GateContext(
        diff_text="some diff",
        diff_hash="hash123",
        changed_files=["file1.py"]
    )
    assert ctx.schema_version == "1.1"
    assert ctx.posture == "strict"
    assert ctx.dispositions == []
    assert ctx.arch_violations == []
    assert ctx.co_change_warnings == []
    assert ctx.review_intensity == "standard"
    assert ctx.todo_delta is None

def test_v1_0_schema_loads_cleanly():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "gate_context_current.json"
        
        # Write v1.0 schema document
        v1_data = {
            "schema_version": "1.0",
            "diff_text": "diff",
            "diff_hash": "hash123",
            "changed_files": ["src/foo.py"]
        }
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(v1_data, f)
            
        loaded = load_gate_context(tmp_path)
        assert loaded is not None
        assert loaded.schema_version == "1.0"
        assert loaded.posture == "strict"
        assert loaded.dispositions == []

def test_atomic_write_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "gate_context_current.json"
        ctx = GateContext(
            diff_text="my diff",
            diff_hash="hash123",
            changed_files=["src/main.py"],
            session_id="session-123"
        )
        ctx.arch_violations = [
            ArchViolation(file="src/main.py", line=10, rule="CLEAN_ARCH", severity="FAIL")
        ]
        ctx.co_change_warnings = [
            CoChangeWarning(file="src/utils.py", confidence="EXTRACTED", reason="import correlation")
        ]
        
        write_gate_context(ctx, tmp_path)
        assert tmp_path.exists()
        
        loaded = load_gate_context(tmp_path)
        assert loaded is not None
        assert loaded.diff_hash == "hash123"
        assert len(loaded.arch_violations) == 1
        assert loaded.arch_violations[0].file == "src/main.py"
        assert loaded.arch_violations[0].severity == "FAIL"
        assert len(loaded.co_change_warnings) == 1
        assert loaded.co_change_warnings[0].confidence == "EXTRACTED"
        assert loaded.session_id == "session-123"

def test_schema_version_mismatch_degrades():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "gate_context_current.json"
        
        # Write incompatible version
        incompatible_data = {
            "schema_version": "2.0",
            "diff_text": "diff",
            "diff_hash": "hash"
        }
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(incompatible_data, f)
            
        loaded = load_gate_context(tmp_path)
        assert loaded is None  # Degrades to None

def test_calculate_todo_delta():
    diff_text = """
+ # TODO: check this
- # TODO: remove this
+ # FIXME: fix that
+ some other added line
    """
    delta = calculate_todo_delta(diff_text)
    assert delta == 1  # 2 added (TODO, FIXME), 1 removed (TODO) -> +1

def test_build_deterministic_findings_section():
    ctx = GateContext(
        diff_text="diff",
        diff_hash="hash",
        changed_files=["src/main.py"],
        review_intensity="elevated"
    )
    ctx.arch_violations = [
        ArchViolation(file="src/main.py", line=5, rule="IMPORT_RULE", severity="WARN")
    ]
    ctx.co_change_warnings = [
        CoChangeWarning(file="src/utils.py", confidence="EXTRACTED", reason="strong correlation")
    ]
    ctx.pytest_collect_status = "src/main.py: 3 tests collected in tests/test_main.py"
    ctx.todo_delta = 2
    
    findings_str = build_deterministic_findings_section(ctx)
    assert "## Deterministic findings (pre-LLM, verified)" in findings_str
    assert "src/main.py:5 — IMPORT_RULE — WARN" in findings_str
    assert "src/utils.py — strong correlation" in findings_str
    assert "src/main.py: 3 tests collected in tests/test_main.py" in findings_str
    assert "TODO/FIXME delta: +2" in findings_str
    assert "Review intensity: elevated" in findings_str


def test_session_id_lifecycle_regression():
    from src.scripts.harness_utils import log_harness_event
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        
        # 1. Log event before session initialization
        log_harness_event({"event_type": "test_pre_init"}, project_root=tmp_root)
        
        # 2. Initialize session in session.json
        state_dir = tmp_root / ".agent" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        session_file = state_dir / "session.json"
        
        expected_uuid = "99999999-8888-7777-6666-555555555555"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump({"session_id": expected_uuid, "status": "ACTIVE"}, f)
            
        # 3. Log event after session initialization
        log_harness_event({"event_type": "test_post_init"}, project_root=tmp_root)
        
        # Read the written events log
        events_path = state_dir / "harness_events.jsonl"
        assert events_path.exists()
        
        lines = events_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        
        evt_pre = json.loads(lines[0])
        evt_post = json.loads(lines[1])
        
        # Verify the fallback is specifically "pre-session-init" and NOT "unknown" or None
        assert evt_pre["session_id"] == "pre-session-init"
        
        # Verify the active session UUID is correctly read
        assert evt_post["session_id"] == expected_uuid

