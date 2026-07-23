"""
Shared helper functions for bootstrap installer and validator scripts.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_harness_repo(path: Path | str) -> bool:
    """Check if the target path is the harness repository itself (or an installation target containing harness_version.txt)."""
    p = Path(path).resolve()
    # Check for harness_version.txt at root
    if (p / "harness_version.txt").exists():
        return True
    return False


def resolve_venv_python(project_path: Path | str) -> Path:
    """Resolve active or local virtual environment Python executable for target project path.
    
    Checks platform-specific venv layout (Scripts/python.exe on Windows, bin/python on POSIX),
    VIRTUAL_ENV/CONDA_PREFIX environment variables, falling back to sys.executable.
    """
    p = Path(project_path).resolve()
    
    # Check local .venv in project directory
    if sys.platform == "win32":
        local_venv = p / ".venv" / "Scripts" / "python.exe"
        if not local_venv.exists():
            local_venv = p / "venv" / "Scripts" / "python.exe"
    else:
        local_venv = p / ".venv" / "bin" / "python"
        if not local_venv.exists():
            local_venv = p / "venv" / "bin" / "python"

    if local_venv.exists():
        return local_venv

    # Check active VIRTUAL_ENV or CONDA_PREFIX
    env_dir = os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")
    if env_dir:
        env_path = Path(env_dir)
        if sys.platform == "win32":
            exe = env_path / "Scripts" / "python.exe"
        else:
            exe = env_path / "bin" / "python"
        if exe.exists():
            return exe

    return Path(sys.executable)
