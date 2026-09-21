"""AST collector for the MC-2 write-site guard (plan 10 task 3; master plan §6.8).

Scans `app/beyo_manager/**/*.py` and `app/scripts/**/*.py` (excluding `app/tests/**`
and `app/migrations/**`) for the six site classes MC-2 names (intention §5B "The
guard"):

    a. every attribute assignment whose target attribute is named `state`
       (`x.state = ...`, `x.state: T = ...`, or `x.state` inside a tuple/list
       assignment target — `a, x.state = ...`);
    b. every `setattr(...)` call;
    c. every `update(Task)` / `insert(Task)` call, including the table object
       (`Task.__table__.update().values(state=...)` and `update(Task.__table__)`);
    d. every `Task(...)` call carrying a `state=` keyword, including a dict
       unpack (`Task(**{"state": ...})`);
    e. every call to `maybe_advance_task_to_working`, `maybe_reopen_task_to_working`,
       `maybe_evaluate_task_ready` or `_apply_step_transition`;
    f. every raw-SQL construct naming the `tasks` table — a `text(...)` call, or a
       `.execute(...)` call, whose literal argument mentions both `tasks` and
       `state` (owner, 2026-09-21, batch C2 review card 4).

The same construct rules also cover `for task.state in ...`, `with ... as task.state`, and
`builtins.setattr(task, "state", ...)`.

**Collection is by construct, not by spelling** (owner, card 4): classes (c), (d)
and (e) are collected **however their names are imported** — a plain name, or a
name bound to a local alias by `from ... import X as Y`. The alias table is built
once per file from that file's own imports and resolves both the callee (`update`/
`insert`/`text`/the four helper names) and, for classes (c)/(d), the `Task` argument
name, before either is matched against its expected spelling.

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
# Names whose *import* alias must be resolved before a call/argument is matched
# against its expected spelling (class-(f) additions of `text`/`execute` are
# resolved structurally, via attribute access or a direct call, not by import
# alias — nobody imports `execute` as a bare name).
_ALIASABLE_NAMES = frozenset({"setattr", "update", "insert", "Task"} | _HELPER_CALL_NAMES)


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


def _collect_import_aliases(tree: ast.Module) -> dict[str, str]:
    """`{local_name: canonical_name}` for every import of one of `_ALIASABLE_NAMES`
    in this file, aliased or not (an un-aliased import maps a name to itself, which
    is a no-op for matching). Only `ast.ImportFrom` binds these names in this
    codebase's convention (no `import sqlalchemy as sa`-style module alias is used
    for `update`/`insert`, and the four helpers are always imported by name)."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in _ALIASABLE_NAMES:
                    aliases[alias.asname or alias.name] = alias.name
    return aliases


def _string_literal_text(node: ast.AST) -> str | None:
    """The literal text of a plain string constant or an f-string's static parts —
    enough to recognize a planted raw-SQL literal without evaluating expressions."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = [
            value.value
            for value in node.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        ]
        return "".join(parts)
    return None


def _iter_assign_targets(target: ast.AST):
    """Flattens a (possibly nested) assignment target: `a, (b.state, c) = ...`
    yields `a`, `b.state` and `c` in turn, so a tuple/list target's `.state`
    element is seen exactly as a bare `x.state = ...` would be."""
    if isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _iter_assign_targets(elt)
    elif isinstance(target, ast.Starred):
        yield from _iter_assign_targets(target.value)
    else:
        yield target


def _dict_unpack_contains_keyword(node: ast.AST, keyword_name: str) -> bool:
    return isinstance(node, ast.Dict) and any(
        isinstance(key, ast.Constant) and key.value == keyword_name for key in node.keys
    )


class _FileVisitor(ast.NodeVisitor):
    def __init__(self, relpath: str, import_aliases: dict[str, str] | None = None):
        self.relpath = relpath
        self.sites: list[WriteSite] = []
        self._function_stack: list[str] = []
        self._import_aliases = import_aliases or {}

    def _enclosing(self) -> str | None:
        return self._function_stack[-1] if self._function_stack else None

    def _resolve(self, name: str | None) -> str | None:
        if name is None:
            return None
        return self._import_aliases.get(name, name)

    def _resolve_callee(self, func: ast.AST) -> str | None:
        """The callee's canonical name, resolving a plain `Name` through this
        file's import-alias table (class (c)/(e)) or reading an `Attribute`'s own
        `.attr` (a bound-method call — `session.execute(...)`, or a module-
        qualified `sa.update(...)`, neither of which is import-aliased)."""
        if isinstance(func, ast.Name):
            return self._resolve(func.id)
        if isinstance(func, ast.Attribute):
            return func.attr
        return None

    def _is_task_table_reference(self, node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "__table__"
            and isinstance(node.value, ast.Name)
            and self._resolve(node.value.id) == "Task"
        )

    def _is_task_table_write_chain(self, node: ast.Call) -> bool:
        """Whether a chained call reaches Task.__table__.update/insert()."""
        current: ast.AST = node.func.value if isinstance(node.func, ast.Attribute) else node
        while isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
            if (
                current.func.attr in {"update", "insert"}
                and not current.args
                and self._is_task_table_reference(current.func.value)
            ):
                return True
            current = current.func.value
        return False

    def _record_attr_state_targets(self, target: ast.AST, lineno: int) -> None:
        for target in _iter_assign_targets(target):
            if isinstance(target, ast.Attribute) and target.attr == "state":
                self.sites.append(
                    WriteSite(
                        self.relpath,
                        lineno,
                        "attr_state",
                        self._enclosing(),
                        f"{_unparse_safe(target.value)}.state",
                    )
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        for top_target in node.targets:
            self._record_attr_state_targets(top_target, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        self._record_attr_state_targets(node.target, node.lineno)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:  # noqa: N802
        self._record_attr_state_targets(node.target, node.lineno)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        self._record_attr_state_targets(node.target, node.lineno)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:  # noqa: N802
        self._record_attr_state_targets(node.target, node.lineno)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:  # noqa: N802
        for item in node.items:
            if item.optional_vars is not None:
                self._record_attr_state_targets(item.optional_vars, node.lineno)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:  # noqa: N802
        for item in node.items:
            if item.optional_vars is not None:
                self._record_attr_state_targets(item.optional_vars, node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        callee = self._resolve_callee(node.func)
        raw_callee_repr = _unparse_safe(node.func)

        if callee == "setattr":
            args_repr = ", ".join(_unparse_safe(arg) for arg in node.args[:2])
            self.sites.append(
                WriteSite(self.relpath, node.lineno, "setattr", self._enclosing(), args_repr)
            )

        elif (
            callee in ("update", "insert")
            and node.args
            and (
                (
                    isinstance(node.args[0], ast.Name)
                    and self._resolve(node.args[0].id) == "Task"
                )
                or self._is_task_table_reference(node.args[0])
            )
        ):
            self.sites.append(
                WriteSite(
                    self.relpath,
                    node.lineno,
                    "update_or_insert_task",
                    self._enclosing(),
                    f"{raw_callee_repr}({_unparse_safe(node.args[0])})",
                )
            )

        elif (
            callee == "Task"
            and (
                any(keyword.arg == "state" for keyword in node.keywords)
                or any(
                    keyword.arg is None
                    and _dict_unpack_contains_keyword(keyword.value, "state")
                    for keyword in node.keywords
                )
            )
        ):
            self.sites.append(
                WriteSite(
                    self.relpath,
                    node.lineno,
                    "task_ctor",
                    self._enclosing(),
                    f"{raw_callee_repr}(state=...)",
                )
            )

        elif (
            callee == "values"
            and any(keyword.arg == "state" for keyword in node.keywords)
            and self._is_task_table_write_chain(node)
        ):
            self.sites.append(
                WriteSite(
                    self.relpath,
                    node.lineno,
                    "update_or_insert_task",
                    self._enclosing(),
                    f"{raw_callee_repr}(state=...)",
                )
            )

        elif callee in _HELPER_CALL_NAMES:
            self.sites.append(
                WriteSite(self.relpath, node.lineno, "helper_call", self._enclosing(), raw_callee_repr)
            )

        elif (
            callee in ("text", "execute")
            and node.args
            and (literal := _string_literal_text(node.args[0])) is not None
            and "tasks" in literal.lower()
            and "state" in literal.lower()
        ):
            self.sites.append(
                WriteSite(
                    self.relpath,
                    node.lineno,
                    "raw_sql_tasks_state",
                    self._enclosing(),
                    _unparse_safe(node)[:120],
                )
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
        aliases = _collect_import_aliases(tree)
        visitor = _FileVisitor(relpath, aliases)
        visitor.visit(tree)
        sites.extend(visitor.sites)

    # A chained table write visits both the outer `.values(...)` call and its
    # inner `.update()` call. The registry is keyed by (path, line), so retain
    # one collected construct per source line just as the guard's contract does.
    unique_sites: dict[tuple[str, int], WriteSite] = {}
    for site in sites:
        unique_sites.setdefault(site.key, site)
    return list(unique_sites.values())


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
