"""AST collector for the MC-2 write-site guard (plan 10 task 3; master plan §6.8).

Scans `app/beyo_manager/**/*.py` and `app/scripts/**/*.py` (excluding `app/tests/**`
and `app/migrations/**`) for the five site classes MC-2 names:

    a. every attribute assignment whose target attribute is named `state`
       (`x.state = ...` or `x.state: T = ...`);
    b. every `setattr(...)` call;
    c. every `update(Task)` / `insert(Task)` call;
    d. every `Task(...)` call carrying a `state=` keyword;
    e. every call to `maybe_advance_task_to_working`, `maybe_reopen_task_to_working`,
       `maybe_evaluate_task_ready` or `_apply_step_transition`.

Each site is identified by `(relpath, lineno, class_)`, `relpath` relative to `app/`.
This module holds no opinion on whether a site is a `Task` write — that judgment is
the registry's (`task_state_write_site_registry.py`), which the test compares this
collector's output against.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parents[5]  # .../backend/app
_SCAN_ROOTS = ("beyo_manager", "scripts")
_EXCLUDED_PARTS = {"tests", "migrations"}
_HELPER_CALL_NAMES = frozenset(
    {
        "maybe_advance_task_to_working",
        "maybe_reopen_task_to_working",
        "maybe_evaluate_task_ready",
        "_apply_step_transition",
    }
)


@dataclass(frozen=True)
class WriteSite:
    relpath: str
    lineno: int
    class_: str  # "attr_state" | "setattr" | "update_or_insert_task" | "task_ctor" | "helper_call"
    enclosing_function: str | None
    detail: str  # a short, human-readable description (target/callee text)

    @property
    def key(self) -> tuple[str, int]:
        return (self.relpath, self.lineno)


def _call_func_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _unparse_safe(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "<?>"


class _FileVisitor(ast.NodeVisitor):
    def __init__(self, relpath: str):
        self.relpath = relpath
        self.sites: list[WriteSite] = []
        self._function_stack: list[str] = []

    def _enclosing(self) -> str | None:
        return self._function_stack[-1] if self._function_stack else None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr == "state":
                self.sites.append(
                    WriteSite(
                        self.relpath,
                        node.lineno,
                        "attr_state",
                        self._enclosing(),
                        f"{_unparse_safe(target.value)}.state",
                    )
                )
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:  # noqa: N802
        target = node.target
        if isinstance(target, ast.Attribute) and target.attr == "state":
            self.sites.append(
                WriteSite(
                    self.relpath,
                    node.lineno,
                    "attr_state",
                    self._enclosing(),
                    f"{_unparse_safe(target.value)}.state",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = _call_func_name(node)

        if isinstance(node.func, ast.Name) and node.func.id == "setattr":
            args_repr = ", ".join(_unparse_safe(arg) for arg in node.args[:2])
            self.sites.append(
                WriteSite(self.relpath, node.lineno, "setattr", self._enclosing(), args_repr)
            )

        elif (
            isinstance(node.func, ast.Name)
            and node.func.id in ("update", "insert")
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "Task"
        ):
            self.sites.append(
                WriteSite(
                    self.relpath,
                    node.lineno,
                    "update_or_insert_task",
                    self._enclosing(),
                    f"{node.func.id}(Task)",
                )
            )

        elif (
            isinstance(node.func, ast.Name)
            and node.func.id == "Task"
            and any(keyword.arg == "state" for keyword in node.keywords)
        ):
            self.sites.append(
                WriteSite(self.relpath, node.lineno, "task_ctor", self._enclosing(), "Task(state=...)")
            )

        elif name in _HELPER_CALL_NAMES:
            self.sites.append(
                WriteSite(self.relpath, node.lineno, "helper_call", self._enclosing(), name)
            )

        self.generic_visit(node)


def _iter_scanned_files():
    for root_name in _SCAN_ROOTS:
        root = _APP_ROOT / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if _EXCLUDED_PARTS & set(path.relative_to(_APP_ROOT).parts):
                continue
            yield path


def collect_write_sites() -> list[WriteSite]:
    sites: list[WriteSite] = []
    for path in _iter_scanned_files():
        relpath = path.relative_to(_APP_ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relpath)
        visitor = _FileVisitor(relpath)
        visitor.visit(tree)
        sites.extend(visitor.sites)
    return sites


def _function_bodies_named(function_name: str):
    """Yields every top-level-or-nested `FunctionDef`/`AsyncFunctionDef` node named
    `function_name`, across every scanned file — a command name is unique enough in
    this codebase's convention (one command per module) that this is unambiguous in
    practice; callers pass a definite name, never a guess."""
    for path in _iter_scanned_files():
        relpath = path.relative_to(_APP_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relpath)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                yield relpath, node


def function_exists(function_name: str) -> bool:
    return any(True for _ in _function_bodies_named(function_name))


def function_contains_call(_relpath: str, function_name: str, callee_name: str) -> bool:
    """True iff some function named `function_name`, anywhere in the scanned
    corpus, contains a call (anywhere in its body, nested included) whose resolved
    name is `callee_name`. `_relpath` is accepted for call-site symmetry with the
    registry but is not required to match — `sync_functions` commonly name a
    different file than the site being classified (e.g. a shared core's internal
    helper call is covered by its callers' own, differently-filed, sync call)."""
    for _found_relpath, node in _function_bodies_named(function_name):
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and _call_func_name(inner) == callee_name:
                return True
    return False


def call_keyword_value_repr(relpath: str, lineno: int, keyword_name: str) -> str | None:
    """The unparsed source of `keyword_name`'s value in the `ast.Call` at
    `(relpath, lineno)`, or `None` if no such call/keyword is found."""
    path = _APP_ROOT / relpath
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=relpath)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.lineno == lineno:
            for keyword in node.keywords:
                if keyword.arg == keyword_name:
                    return _unparse_safe(keyword.value)
    return None
