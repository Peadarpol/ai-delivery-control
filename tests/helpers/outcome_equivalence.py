"""Reusable outcome-equivalence test pattern.

Delivers Scenario 6 of ``SPEC-loop-closure-verification.md`` (T1-K-19, Phase C).

Why this exists
---------------
The spec's §0 Motivation Gate names two founding incidents. The second one was a refactor
that claimed to preserve a project's operational schema-hardening exemption data while
changing its storage mechanism (inline Python constants -> config-driven YAML), and
silently emptied it instead. The full suite passed 550/550 throughout, because every test
asserted *the code still runs*, and none asserted *the specific data survived*.

This module is the general mechanism for asserting the latter. A refactor that claims
"behavior is preserved for project X" is verified here by pinning the specific values X
depends on, running the refactor, and re-reading those same values from wherever the
refactor claims to have put them.

Deliberately general
--------------------
Nothing here is specific to schema hardening, or to any one migration. A :class:`ValueLocator`
is ``(logical name, artifact relative path, dotted key path)``, so any future spec touching
any shared YAML/JSON artifact can reuse this directly — which is the point of shipping a
helper rather than a one-off test (see spec §5, Phase C: "for any future refactor claiming
behavior-preservation").

The refactor-relocates-values case is first-class: ``after_locators`` may point at a
different artifact and/or key path than ``before_locators``. Without that, a *correct*
relocation would be indistinguishable from a deletion.

Typical use::

    BEFORE = (
        ValueLocator("schema_whitelist", ".agent/config.yaml", "schema_hardening.whitelist"),
        ValueLocator("exempt_tables", ".agent/config.yaml", "schema_hardening.exempt_tables"),
    )
    AFTER = tuple(loc.relocated(artifact=".agent/config/schema_hardening.yaml") for loc in BEFORE)

    assert_refactor_preserves_values(project_root, BEFORE, my_refactor, after_locators=AFTER)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Sequence

import yaml

__all__ = [
    "MISSING",
    "ValueLocator",
    "OutcomeEquivalenceError",
    "materialize_fixture_project",
    "load_operational_values",
    "apply_refactor",
    "assert_values_preserved",
    "assert_refactor_preserves_values",
]


class _Missing:
    """Sentinel for 'this value is not present at all'.

    Deliberately distinct from ``[]``/``{}``/``None``: the founding incident emptied values
    rather than removing them, and the two failure shapes are worth reporting differently.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<MISSING>"

    def __bool__(self) -> bool:
        return False


MISSING = _Missing()


class OutcomeEquivalenceError(AssertionError):
    """Raised when tracked values are not preserved across a refactor.

    Subclasses :class:`AssertionError` so it reads as a normal test failure to pytest while
    remaining catchable by type when a test needs to inspect the diagnosis.
    """

    def __init__(self, message: str, differences: Sequence["_Difference"]):
        super().__init__(message)
        self.differences = tuple(differences)

    @property
    def failed_names(self) -> tuple[str, ...]:
        """Logical names of the tracked values that were not preserved."""
        return tuple(d.name for d in self.differences)


@dataclass(frozen=True)
class ValueLocator:
    """Addresses one tracked value inside a project fixture.

    Args:
        name: Logical, storage-independent name for the value (e.g. ``"exempt_tables"``).
            Before/after locators are matched on this, so it must survive the refactor even
            when the artifact and key path do not.
        artifact: Path to the containing file, relative to the project root. ``.yaml``/``.yml``
            and ``.json`` are parsed; any other suffix raises.
        key_path: Dot-separated path to the value within the parsed artifact
            (e.g. ``"schema_hardening.exempt_tables"``). Use ``""`` for the whole document.
            Literal dots inside a single key are not supported — a documented limitation, not
            a silent one; such a key will simply resolve to ``MISSING``.
    """

    name: str
    artifact: str
    key_path: str

    def relocated(self, *, artifact: str | None = None, key_path: str | None = None) -> "ValueLocator":
        """Return a copy pointing at a new storage location, keeping ``name`` fixed.

        This is how a refactor's claimed new home is expressed for the ``after`` snapshot.
        """
        return replace(
            self,
            artifact=self.artifact if artifact is None else artifact,
            key_path=self.key_path if key_path is None else key_path,
        )

    def describe(self) -> str:
        return f"{self.artifact}::{self.key_path or '<document root>'}"


@dataclass(frozen=True)
class _Difference:
    """One tracked value that failed to survive the refactor."""

    name: str
    kind: str  # DROPPED | EMPTIED | CHANGED
    before_locator: ValueLocator
    after_locator: ValueLocator
    before_value: Any
    after_value: Any
    missing_members: tuple[Any, ...] = ()
    added_members: tuple[Any, ...] = ()

    def render(self) -> str:
        lines = [
            f"  - {self.name} [{self.kind}]",
            f"      before: {self.before_locator.describe()} = {_render_value(self.before_value)}",
            f"      after : {self.after_locator.describe()} = {_render_value(self.after_value)}",
        ]
        if self.missing_members:
            lines.append(f"      dropped member(s): {_render_value(list(self.missing_members))}")
        if self.added_members:
            lines.append(f"      unexpected new member(s): {_render_value(list(self.added_members))}")
        return "\n".join(lines)


def _render_value(value: Any) -> str:
    if value is MISSING:
        return "<MISSING>"
    if isinstance(value, (list, tuple, set, frozenset)):
        return repr(sorted((str(v) for v in value)))
    return repr(value)


# ── Fixture materialization ──────────────────────────────────────────────────


def materialize_fixture_project(fixture_dir: Path, dest_dir: Path) -> Path:
    """Copy a checked-in fixture project into a scratch directory and return the copy's root.

    Refactors mutate project state, so they must never run against the checked-in fixture.
    Call this with a ``tmp_path``-derived destination.
    """
    import shutil

    fixture_dir = Path(fixture_dir)
    dest_dir = Path(dest_dir)
    if not fixture_dir.is_dir():
        raise FileNotFoundError(f"Fixture project not found: {fixture_dir}")
    shutil.copytree(fixture_dir, dest_dir, dirs_exist_ok=True)
    return dest_dir


# ── Snapshotting ─────────────────────────────────────────────────────────────


def _parse_artifact(path: Path) -> Any:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    if suffix == ".json":
        return json.loads(text)
    raise ValueError(
        f"Unsupported artifact type for outcome-equivalence tracking: {path.name} "
        f"(supported: .yaml, .yml, .json)"
    )


def _resolve_key_path(document: Any, key_path: str) -> Any:
    if not key_path:
        return document if document is not None else MISSING
    node = document
    for segment in key_path.split("."):
        if not isinstance(node, dict) or segment not in node:
            return MISSING
        node = node[segment]
    return node


def load_operational_values(
    project_root: Path, locators: Iterable[ValueLocator]
) -> Dict[str, Any]:
    """Read each locator's current value out of the project, keyed by logical name.

    A locator whose artifact does not exist, or whose key path does not resolve, yields
    :data:`MISSING` rather than raising — absence is a finding to report, not an error to
    crash on, since detecting exactly that absence is this module's job.
    """
    project_root = Path(project_root)
    snapshot: Dict[str, Any] = {}
    for locator in locators:
        if locator.name in snapshot:
            raise ValueError(f"Duplicate locator name in snapshot: {locator.name!r}")
        artifact_path = project_root / locator.artifact
        if not artifact_path.is_file():
            snapshot[locator.name] = MISSING
            continue
        snapshot[locator.name] = _resolve_key_path(_parse_artifact(artifact_path), locator.key_path)
    return snapshot


# ── Refactor application ─────────────────────────────────────────────────────


def apply_refactor(project_root: Path, refactor: Callable[[Path], Any]) -> Any:
    """Apply a caller-supplied refactor to the project's state and return whatever it returns.

    ``refactor`` takes the project root and mutates it in place. Exceptions propagate
    unchanged — a refactor that crashes is a different (and already-visible) failure from the
    silent-data-loss shape this module exists to catch, and must not be reported as one.
    """
    project_root = Path(project_root)
    if not project_root.is_dir():
        raise FileNotFoundError(f"Project root not found: {project_root}")
    return refactor(project_root)


# ── Assertion ────────────────────────────────────────────────────────────────


def _is_collection(value: Any) -> bool:
    return isinstance(value, (list, tuple, set, frozenset))


def _is_empty(value: Any) -> bool:
    if value is MISSING or value is None:
        return True
    if isinstance(value, (list, tuple, set, frozenset, dict, str)):
        return len(value) == 0
    return False


def _classify(
    name: str,
    before_locator: ValueLocator,
    after_locator: ValueLocator,
    before: Any,
    after: Any,
    *,
    collections_as_sets: bool,
) -> _Difference | None:
    """Return a :class:`_Difference` if ``after`` failed to preserve ``before``, else ``None``."""
    if before is MISSING and after is MISSING:
        return None

    equal = _values_equal(before, after, collections_as_sets=collections_as_sets)
    if equal:
        return None

    if after is MISSING:
        kind = "DROPPED"
    elif not _is_empty(before) and _is_empty(after):
        kind = "EMPTIED"
    else:
        kind = "CHANGED"

    missing_members: tuple[Any, ...] = ()
    added_members: tuple[Any, ...] = ()
    if _is_collection(before):
        before_members = {str(v) for v in before}
        after_members = {str(v) for v in after} if _is_collection(after) else set()
        missing_members = tuple(sorted(before_members - after_members))
        added_members = tuple(sorted(after_members - before_members))

    return _Difference(
        name=name,
        kind=kind,
        before_locator=before_locator,
        after_locator=after_locator,
        before_value=before,
        after_value=after,
        missing_members=missing_members,
        added_members=added_members,
    )


def _values_equal(before: Any, after: Any, *, collections_as_sets: bool) -> bool:
    if before is MISSING or after is MISSING:
        return before is after
    if collections_as_sets and _is_collection(before) and _is_collection(after):
        return {str(v) for v in before} == {str(v) for v in after}
    return before == after


def assert_values_preserved(
    before: Dict[str, Any],
    after: Dict[str, Any],
    before_locators: Sequence[ValueLocator],
    after_locators: Sequence[ValueLocator],
    *,
    context: str = "",
    collections_as_sets: bool = True,
) -> None:
    """Assert every tracked value survived, naming exactly which ones did not.

    Args:
        before: Snapshot from :func:`load_operational_values` taken before the refactor.
        after: Snapshot taken after it.
        before_locators / after_locators: Used only to render *where* each value was looked
            for, so a failure message points at real paths rather than logical names alone.
        context: Optional description of the refactor under test, echoed in the failure.
        collections_as_sets: When True (default), list/set values compare by membership, not
            order — correct for whitelist/exemption artifacts, where ordering carries no
            meaning. Set False when order is part of the contract.

    Raises:
        OutcomeEquivalenceError: naming each unpreserved value, its classification
            (``DROPPED`` / ``EMPTIED`` / ``CHANGED``), both storage locations, and — for
            collections — the specific members that went missing.
    """
    before_by_name = {loc.name: loc for loc in before_locators}
    after_by_name = {loc.name: loc for loc in after_locators}

    tracked = list(before_by_name)
    differences = []
    for name in tracked:
        diff = _classify(
            name,
            before_by_name[name],
            after_by_name.get(name, before_by_name[name]),
            before.get(name, MISSING),
            after.get(name, MISSING),
            collections_as_sets=collections_as_sets,
        )
        if diff is not None:
            differences.append(diff)

    if not differences:
        return

    # ASCII-only message body: this text is printed by pytest on Windows consoles using a
    # cp1252 code page, where a non-ASCII character can mangle or break the very failure
    # report the caller needs. Same reasoning as the harness scripts' safe_print().
    header = (
        f"Outcome equivalence FAILED - {len(differences)} of {len(tracked)} tracked value(s) "
        f"were not preserved across the refactor"
    )
    if context:
        header += f" [{context}]"
    message = "\n".join([header + ":", ""] + [d.render() for d in differences])
    message += (
        "\n\nThe refactor claimed to preserve these values while changing their storage. "
        "It did not."
    )
    raise OutcomeEquivalenceError(message, differences)


def assert_refactor_preserves_values(
    project_root: Path,
    before_locators: Sequence[ValueLocator],
    refactor: Callable[[Path], Any],
    *,
    after_locators: Sequence[ValueLocator] | None = None,
    context: str = "",
    collections_as_sets: bool = True,
) -> Dict[str, Any]:
    """Snapshot, apply the refactor, re-snapshot, and assert equivalence — the full pattern.

    Args:
        project_root: A scratch copy of a fixture project (see :func:`materialize_fixture_project`).
        before_locators: Where the tracked values live before the refactor.
        refactor: Callable taking the project root and mutating it in place.
        after_locators: Where the refactor claims the values now live. Defaults to
            ``before_locators`` (i.e. the refactor claims not to have moved them).
        context: Optional description echoed in any failure message.
        collections_as_sets: See :func:`assert_values_preserved`.

    Returns:
        The post-refactor snapshot, so callers can make further assertions on it.

    Raises:
        OutcomeEquivalenceError: if any tracked value was dropped, emptied, or changed.
    """
    effective_after = list(after_locators) if after_locators is not None else list(before_locators)
    before = load_operational_values(project_root, before_locators)
    apply_refactor(project_root, refactor)
    after = load_operational_values(project_root, effective_after)
    assert_values_preserved(
        before,
        after,
        list(before_locators),
        effective_after,
        context=context,
        collections_as_sets=collections_as_sets,
    )
    return after
