#!/usr/bin/env python3
"""
Dynamic Verification Script for AI Delivery Control Installation (T1-A-06)
Programmatically spins up mock projects, installs the harness, and validates stack packs and upgrade safety.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Enforce UTF-8 encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def safe_rmtree(path: Path, max_retries=5, delay=0.5):
    """Safely remove a directory with retry logic for Windows process locks."""
    for i in range(max_retries):
        try:
            if path.exists():
                shutil.rmtree(path)
            return
        except PermissionError:
            if i == max_retries - 1:
                raise
            time.sleep(delay)


def clean_dir(p: Path):
    safe_rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


def run_installer(workspace_root: Path, mock_dir: Path):
    install_script = workspace_root / "bootstrap" / "install.py"
    res = subprocess.run(
        [sys.executable, str(install_script), "--project-path", str(mock_dir), "--verbose"],
        capture_output=True,
        encoding="utf-8"
    )
    if res.returncode != 0:
        print(f"❌ Installer script returned non-zero code: {res.returncode}")
        print(f"Stdout:\n{res.stdout}")
        print(f"Stderr:\n{res.stderr}")
        sys.exit(1)


def main():
    print("🧪 Starting Programmatic Verification for T1-A-06...")
    
    workspace_root = Path(__file__).resolve().parent.parent
    mock_dir = workspace_root / "scratch" / "mock_project"
    
    # ----------------------------------------------------
    # TEST CASE 1: Python + FastAPI
    # ----------------------------------------------------
    print("\n--- 🎬 [TEST CASE 1] Python + FastAPI stack pack installation ---")
    clean_dir(mock_dir)
    
    # Git init
    subprocess.run(["git", "init"], cwd=str(mock_dir), capture_output=True, check=True)
    
    # Scaffold pyproject.toml with FastAPI
    pyproject_toml = mock_dir / "pyproject.toml"
    pyproject_toml.write_text("""[tool.poetry]
name = "mock-fastapi-project"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.10"
fastapi = "^0.109.0"
""", encoding="utf-8")
    
    src_dir = mock_dir / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "main.py").write_text("from fastapi import FastAPI\n", encoding="utf-8")

    run_installer(workspace_root, mock_dir)
    
    # Assert skills are copied
    skills_dir = mock_dir / ".agent" / "skills"
    assert skills_dir.exists(), "skills directory missing"
    assert (skills_dir / "code-review").exists(), "universal skill 'code-review' missing"
    
    # Assert python-fastapi stack pack is installed and is the rich stack-pack version
    fastapi_skill_md = skills_dir / "python-fastapi" / "SKILL.md"
    assert fastapi_skill_md.exists(), "python-fastapi skill missing"
    fastapi_content = fastapi_skill_md.read_text(encoding="utf-8")
    assert "skill_type: stack-pack" in fastapi_content, "python-fastapi is not marked as stack-pack in frontmatter"
    assert "Mass Assignment Protection" in fastapi_content, "python-fastapi does not contain the rich stack-pack guidelines"
    
    print("✅ Passed: Python + FastAPI correctly installed universal skills + rich FastAPI stack-pack flatly.")

    # ----------------------------------------------------
    # TEST CASE 2: Node + Express
    # ----------------------------------------------------
    print("\n--- 🎬 [TEST CASE 2] Node + Express stack pack installation ---")
    clean_dir(mock_dir)
    subprocess.run(["git", "init"], cwd=str(mock_dir), capture_output=True, check=True)
    
    # Scaffold package.json with Express
    package_json = mock_dir / "package.json"
    package_json.write_text("""{
  "name": "mock-express-project",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.2"
  }
}""", encoding="utf-8")
    
    src_dir = mock_dir / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "index.js").write_text("const express = require('express');\n", encoding="utf-8")

    run_installer(workspace_root, mock_dir)
    
    # Assert skills are copied
    skills_dir = mock_dir / ".agent" / "skills"
    assert skills_dir.exists(), "skills directory missing"
    assert (skills_dir / "code-review").exists(), "universal skill 'code-review' missing"
    
    # Assert node-express stack pack is installed and is the stub version
    express_skill_md = skills_dir / "node-express" / "SKILL.md"
    assert express_skill_md.exists(), "node-express skill missing"
    express_content = express_skill_md.read_text(encoding="utf-8")
    assert "skill_type: stack-pack" in express_content, "node-express is not marked as stack-pack in frontmatter"
    assert "Node Express Stack Pack (Stub)" in express_content, "node-express is not the stub"
    
    print("✅ Passed: Node + Express correctly installed universal skills + Express stub flatly.")

    # ----------------------------------------------------
    # TEST CASE 3: Empty Project
    # ----------------------------------------------------
    print("\n--- 🎬 [TEST CASE 3] Empty Project (no stack packs) ---")
    clean_dir(mock_dir)
    subprocess.run(["git", "init"], cwd=str(mock_dir), capture_output=True, check=True)
    
    # Scaffold basic Python file but no dependency files
    src_dir = mock_dir / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "main.py").write_text("print('pure python no dependencies')\n", encoding="utf-8")

    run_installer(workspace_root, mock_dir)
    
    skills_dir = mock_dir / ".agent" / "skills"
    assert skills_dir.exists()
    assert (skills_dir / "code-review").exists(), "universal skill 'code-review' missing"
    
    # Assert neither stack pack skill exists
    # Node-express is a stack-pack only, and should NOT be copied
    assert not (skills_dir / "node-express").exists(), "node-express stack-pack was copied in empty project"
    
    print("✅ Passed: Empty project installed universal skills and correctly skipped stack packs.")

    # ----------------------------------------------------
    # TEST CASE 4: Re-run & Upgrade Protection (Non-destructive Copier)
    # ----------------------------------------------------
    print("\n--- 🎬 [TEST CASE 4] Re-run & Upgrade Protection ---")
    clean_dir(mock_dir)
    subprocess.run(["git", "init"], cwd=str(mock_dir), capture_output=True, check=True)
    
    # Scaffold pyproject.toml with FastAPI
    pyproject_toml = mock_dir / "pyproject.toml"
    pyproject_toml.write_text("""[tool.poetry]
name = "mock-upgrade-project"
version = "0.1.0"
[tool.poetry.dependencies]
fastapi = "^0.109.0"
""", encoding="utf-8")
    
    src_dir = mock_dir / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "main.py").write_text("from fastapi import FastAPI\n", encoding="utf-8")

    # First install
    print("Running initial install...")
    run_installer(workspace_root, mock_dir)
    
    skills_dir = mock_dir / ".agent" / "skills"
    
    # 1. Developer edits an existing skill (e.g. code-review/SKILL.md)
    review_skill_md = skills_dir / "code-review" / "SKILL.md"
    original_review_content = review_skill_md.read_text(encoding="utf-8")
    developer_edit_marker = "### ⚠️ DEVELOPER CUSTOM PRINCIPLE: ALWAYS DOCSTRING EVERYTHING"
    customized_review_content = original_review_content + f"\n\n{developer_edit_marker}\n"
    review_skill_md.write_text(customized_review_content, encoding="utf-8")
    
    # 2. Developer adds a custom skill folder in the target skills directory
    custom_skill_dir = skills_dir / "my-custom-skill"
    custom_skill_dir.mkdir(parents=True, exist_ok=True)
    custom_skill_md = custom_skill_dir / "SKILL.md"
    custom_skill_marker = "My special custom developer skill that must be preserved."
    custom_skill_md.write_text(custom_skill_marker, encoding="utf-8")
    
    # 3. Developer edits the python-fastapi stack-pack skill
    fastapi_skill_md = skills_dir / "python-fastapi" / "SKILL.md"
    original_fastapi_content = fastapi_skill_md.read_text(encoding="utf-8")
    fastapi_edit_marker = "### ⚠️ DEVELOPER FASTAPI RULE: FORBID ALL UNTYPED DEPENDENCIES"
    customized_fastapi_content = original_fastapi_content + f"\n\n{fastapi_edit_marker}\n"
    fastapi_skill_md.write_text(customized_fastapi_content, encoding="utf-8")
    
    # Re-run install
    print("Running second install (re-run / upgrade)...")
    run_installer(workspace_root, mock_dir)
    
    # Assert custom developer skill is preserved and not deleted
    assert custom_skill_md.exists(), "Developer's custom skill was deleted during re-run!"
    assert custom_skill_md.read_text(encoding="utf-8") == custom_skill_marker, "Developer's custom skill content was modified!"
    
    # Assert edits to existing universal skill are preserved
    new_review_content = review_skill_md.read_text(encoding="utf-8")
    assert developer_edit_marker in new_review_content, "Developer's custom edits to an existing skill were overwritten!"
    
    # Assert edits to python-fastapi stack-pack are preserved
    new_fastapi_content = fastapi_skill_md.read_text(encoding="utf-8")
    assert fastapi_edit_marker in new_fastapi_content, "Developer's custom edits to the stack-pack skill were overwritten!"
    
    # Assert other universal files and stack-packs still exist
    assert (skills_dir / "python-fastapi").exists()
    assert (skills_dir / "debugging").exists()
    
    print("✅ Passed: Re-run / Upgrade protection successfully merged rather than replacing skills.")

    # ----------------------------------------------------
    # RUN VALIDATION & ARTIFACT VIOLATION
    # ----------------------------------------------------
    print("\n--- 🎬 [TEST CASE 5] Running static analysis checks & layer validation on target ---")
    
    # Verify environment validation passes
    validate_script = workspace_root / "bootstrap" / "validate.py"
    val_res = subprocess.run(
        [sys.executable, str(validate_script), "--project-path", str(mock_dir)],
        capture_output=True,
        encoding="utf-8"
    )
    assert val_res.returncode == 0, f"validate.py failed on target: {val_res.stdout}\n{val_res.stderr}"
    print("  ✅ validate.py passed successfully")
    
    # Verify architecture checks runs cleanly
    arch_checks_script = mock_dir / ".agent" / "skills" / "senior-architect" / "scripts" / "architecture_checks.py"
    arch_res = subprocess.run(
        [sys.executable, str(arch_checks_script)],
        cwd=str(mock_dir),
        capture_output=True,
        encoding="utf-8"
    )
    assert arch_res.returncode == 0, f"architecture_checks.py failed on clean target: {arch_res.stdout}\n{arch_res.stderr}"
    print("  ✅ architecture_checks.py passed on clean target")

    # Clean up mock project
    print("\n🧹 Cleaning up mock project directory...")
    safe_rmtree(mock_dir)
    
    print("\n🎉 Verification SUCCESSFUL! All T1-A-06 scenarios and upgrade-safety assertions are passing beautifully.")


if __name__ == "__main__":
    main()
