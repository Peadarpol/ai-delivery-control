"""Co-change check — thin re-export layer over co_change_core (SPEC §5).

All logic lives in ``co_change_core``.  This module exists solely to preserve the
public import path that downstream scripts rely on.
"""

from co_change_core import (
    build_co_change_map,
    check_refactor_keyword,
    get_ast_imports,
    get_git_co_changes,
    load_co_change_map,
    run_co_change_estimator,
)

__all__ = [
    "build_co_change_map",
    "check_refactor_keyword",
    "get_ast_imports",
    "get_git_co_changes",
    "load_co_change_map",
    "run_co_change_estimator",
]