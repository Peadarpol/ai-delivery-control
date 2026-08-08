#!/usr/bin/env python3
"""
.agent/scripts/contract_test_runner.py — Automated Producer/Consumer Contract Test Runner (Tier 4, D1)

Executes contract tests defined in .agent/config/producer_consumer_contracts.yaml in isolated temporary environments.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yaml


# Ensure src/scripts is in sys.path for harness_utils
_bootstrap_path = Path(__file__).resolve()
_bootstrap_root = None
for _p in [_bootstrap_path] + list(_bootstrap_path.parents):
    if (_p / ".git").exists() or (_p / ".agent").exists():
        _bootstrap_root = _p
        break
if _bootstrap_root and str(_bootstrap_root / "src" / "scripts") not in sys.path:
    sys.path.insert(0, str(_bootstrap_root / "src" / "scripts"))

try:
    from src.scripts.harness_utils import _find_project_root
except ImportError:
    from harness_utils import _find_project_root


PROJECT_ROOT = _find_project_root()


def render_templates(target_dir: Path) -> dict[str, str]:
    """Dynamically render relative date placeholders in template files inside target_dir."""
    now_utc = datetime.now(timezone.utc)
    date_25d = (now_utc - timedelta(days=25)).strftime("%Y-%m-%d")

    rendered_timestamps = {"NOW_MINUS_25D": date_25d}

    for template_file in list(target_dir.rglob("*.template")):
        content = template_file.read_text(encoding="utf-8")
        rendered_content = content.replace("{NOW_MINUS_25D}", date_25d)
        
        target_file = template_file.parent / template_file.stem
        target_file.write_text(rendered_content, encoding="utf-8")
        template_file.unlink()

    return rendered_timestamps


def run_contract_test(contract: dict, verbose: bool = False) -> tuple[bool, str, dict[str, str]]:
    """Execute a single contract test in an isolated temporary directory."""
    name = contract.get("name", "unnamed_contract")
    fixture_rel = contract.get("fixture_dir", "")
    fixture_dir = (PROJECT_ROOT / fixture_rel).resolve()

    if not fixture_dir.exists():
        return False, f"Fixture directory not found: {fixture_dir}", {}

    producer_cfg = contract.get("producer", {})
    consumer_cfg = contract.get("consumer", {})
    assert_mode = contract.get("assert", "consumer_does_not_silently_skip")

    original_cwd = os.getcwd()

    with tempfile.TemporaryDirectory(prefix=f"contract_test_{name}_") as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        # 1. Copy fixture directory content into tempdir
        shutil.copytree(fixture_dir, tmpdir, dirs_exist_ok=True)

        # Ensure required directories exist
        (tmpdir / ".agent" / "state" / "dream_proposals").mkdir(parents=True, exist_ok=True)
        (tmpdir / ".agent" / "config").mkdir(parents=True, exist_ok=True)

        # 2. Render templates with relative timestamps
        rendered_timestamps = render_templates(tmpdir)

        # 3. Execute Producer
        prod_type = producer_cfg.get("type")
        if prod_type == "cli":
            cmd = producer_cfg.get("command", [])
            # Resolve script path relative to PROJECT_ROOT if needed
            resolved_cmd = []
            for token in cmd:
                if token.endswith(".py") and (PROJECT_ROOT / token).exists():
                    resolved_cmd.append(str((PROJECT_ROOT / token).resolve()))
                else:
                    resolved_cmd.append(token)

            res = subprocess.run(
                resolved_cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0 and verbose:
                print(f"[PRODUCER STDOUT]\n{res.stdout}")
                print(f"[PRODUCER STDERR]\n{res.stderr}")
        else:
            return False, f"Unsupported producer type: {prod_type}", rendered_timestamps

        # 4. Assert Producer Output & Schema Line
        proposals_dir = tmpdir / ".agent" / "state" / "dream_proposals"
        open_cards = list(proposals_dir.glob("*__open.md"))
        if not open_cards:
            return (
                False,
                f"Producer failed to generate open proposal card in {proposals_dir}. Producer stdout: {res.stdout.strip()}",
                rendered_timestamps,
            )

        card_content = open_cards[0].read_text(encoding="utf-8")
        has_generated_line = bool(re.search(r"Generated:\s*\d{4}-\d{2}-\d{2}", card_content))
        if not has_generated_line:
            return (
                False,
                f"Producer proposal card '{open_cards[0].name}' lacks required contract field '- Generated: YYYY-MM-DD'.",
                rendered_timestamps,
            )

        # 5. Execute Consumer
        cons_type = consumer_cfg.get("type")
        consumer_stdout = ""
        if cons_type == "function":
            mod_rel = consumer_cfg.get("module", "")
            func_name = consumer_cfg.get("call", "")
            mod_path = (PROJECT_ROOT / mod_rel).resolve()

            if not mod_path.exists():
                return False, f"Consumer module path not found: {mod_path}", rendered_timestamps

            # Import module dynamically
            spec = importlib.util.spec_from_file_location("contract_consumer_mod", mod_path)
            if not spec or not spec.loader:
                return False, f"Could not load module spec for {mod_path}", rendered_timestamps
            module = importlib.util.module_from_spec(spec)
            
            # Ensure src/scripts is in sys.path for harness imports inside module
            src_scripts = PROJECT_ROOT / "src" / "scripts"
            agent_scripts = PROJECT_ROOT / ".agent" / "scripts"
            for p in [str(src_scripts), str(agent_scripts)]:
                if p not in sys.path:
                    sys.path.insert(0, p)

            spec.loader.exec_module(module)
            target_func = getattr(module, func_name, None)
            if not target_func:
                return False, f"Function '{func_name}' not found in {mod_path}", rendered_timestamps

            # Execute function with cwd = tmpdir
            stdout_buf = io.StringIO()
            try:
                os.chdir(tmpdir)
                old_stdout = sys.stdout
                sys.stdout = stdout_buf
                target_func()
            finally:
                sys.stdout = old_stdout
                os.chdir(original_cwd)

            consumer_stdout = stdout_buf.getvalue()
        else:
            return False, f"Unsupported consumer type: {cons_type}", rendered_timestamps

        # 6. Assert Consumer Mode
        if assert_mode == "consumer_does_not_silently_skip":
            if "Status         : NO PROPOSALS DIR" in consumer_stdout:
                return False, "Consumer failed: output contained 'NO PROPOSALS DIR'", rendered_timestamps
            if "CLEAN (no open proposals)" in consumer_stdout:
                return False, "Consumer failed: output contained 'CLEAN (no open proposals)'", rendered_timestamps
            if "Open proposals :" not in consumer_stdout:
                return False, f"Consumer failed: output missing 'Open proposals :'. Captured:\n{consumer_stdout}", rendered_timestamps

            msg = f"Contract '{name}' PASSED.\nRendered Date: {rendered_timestamps.get('NOW_MINUS_25D')}\nConsumer Output:\n{consumer_stdout.strip()}"
            return True, msg, rendered_timestamps
        else:
            return False, f"Unknown assert mode: {assert_mode}", rendered_timestamps


def main() -> int:
    parser = argparse.ArgumentParser(description="Producer/Consumer Contract Test Runner")
    parser.add_argument("--contract", help="Specific contract name to run")
    parser.add_argument("--verbose", action="store_true", help="Print verbose details")
    args = parser.parse_args()

    config_path = PROJECT_ROOT / ".agent" / "config" / "producer_consumer_contracts.yaml"
    if not config_path.exists():
        print(f"❌ Error: Config file not found at {config_path}", file=sys.stderr)
        return 1

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg_data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"❌ Error parsing contract config: {e}", file=sys.stderr)
        return 1

    contracts = cfg_data.get("contracts", [])
    if not contracts:
        print("❌ Error: No contracts defined in config.", file=sys.stderr)
        return 1

    all_passed = True
    for c in contracts:
        c_name = c.get("name", "unnamed")
        if args.contract and c_name != args.contract:
            continue

        print(f"=== Running Contract Test: {c_name} ===")
        passed, msg, timestamps = run_contract_test(c, verbose=args.verbose)
        if passed:
            print(f"✅ PASS: {msg}\n")
        else:
            print(f"❌ FAIL: {msg}\n", file=sys.stderr)
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
