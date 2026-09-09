import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.queries.tasks.tasks import _build_order_by


WORKSPACE_ID = "wsp_test"


def _compile(clause) -> str:
    return str(
        clause.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def _rendered(order_by, **kwargs) -> list[str]:
    kwargs.setdefault("workspace_id", WORKSPACE_ID)
    return [_compile(clause) for clause in _build_order_by(order_by, **kwargs)]


def _rendered_in_statement(order_by, **kwargs) -> str:
    """Render the clauses inside a real statement so correlation is resolved."""
    kwargs.setdefault("workspace_id", WORKSPACE_ID)
    stmt = select(Task.client_id).order_by(*_build_order_by(order_by, **kwargs))
    return _compile(stmt)


_DEFAULT = [
    "tasks.ready_by_at ASC NULLS LAST",
    (
        "CASE WHEN (tasks.priority = 'urgent') THEN 4 WHEN (tasks.priority = 'high') THEN 3 "
        "WHEN (tasks.priority = 'normal') THEN 2 WHEN (tasks.priority = 'low') THEN 1 ELSE 0 END DESC"
    ),
    "tasks.created_at ASC",
    "tasks.client_id ASC",
]


@pytest.mark.unit
def test_default_ordering_ends_on_the_primary_key() -> None:
    assert _rendered(None) == _DEFAULT


@pytest.mark.unit
@pytest.mark.parametrize("order_by", ["bogus", "", "   ", "not_a_field:desc"])
def test_unrecognised_keys_fall_back_to_the_default(order_by) -> None:
    assert _rendered(order_by) == _DEFAULT


@pytest.mark.unit
@pytest.mark.parametrize(
    "order_by, expected",
    [
        ("ready_by_at", "tasks.ready_by_at ASC NULLS LAST"),
        ("ready_by_at:desc", "tasks.ready_by_at DESC"),
        ("created_at", "tasks.created_at ASC"),
        ("created_at:desc", "tasks.created_at DESC"),
        ("created_at:DESC", "tasks.created_at DESC"),
        ("scheduled_start_at", "tasks.scheduled_start_at ASC"),
        ("scheduled_end_at:desc", "tasks.scheduled_end_at DESC"),
    ],
)
def test_legacy_keys_are_unchanged(order_by, expected) -> None:
    """Characterization: the five pre-existing keys must render exactly as before."""
    assert _rendered(order_by) == [expected, "tasks.client_id ASC"]


@pytest.mark.unit
def test_legacy_priority_key_is_unchanged() -> None:
    clauses = _rendered("priority:desc")
    assert clauses == [_DEFAULT[1], "tasks.client_id ASC"]


@pytest.mark.unit
def test_multiple_legacy_keys_keep_their_order() -> None:
    assert _rendered("priority:desc,created_at") == [
        _DEFAULT[1],
        "tasks.created_at ASC",
        "tasks.client_id ASC",
    ]


# --- recently_completed -------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("task_states", [None, [], ["working"], ["pending", "assigned"]])
def test_recently_completed_is_rejected_without_a_completed_state_filter(task_states) -> None:
    """The guard: outside a ready/resolved cohort the key is not answerable, so it must
    degrade to the default ordering rather than return a page ordered by all-NULL."""
    assert _rendered("recently_completed", task_states=task_states) == _DEFAULT


@pytest.mark.unit
@pytest.mark.parametrize("task_states", [["ready"], ["resolved"], ["ready", "resolved"], ["working", "ready"]])
def test_recently_completed_is_honored_with_a_completed_state_filter(task_states) -> None:
    assert _rendered("recently_completed", task_states=task_states) == [
        "tasks.completed_at DESC NULLS LAST",
        "tasks.client_id ASC",
    ]


@pytest.mark.unit
@pytest.mark.parametrize("task_states", [["READY"], ["Resolved"], [" ready "]])
def test_recently_completed_guard_is_case_and_whitespace_insensitive(task_states) -> None:
    assert _rendered("recently_completed", task_states=task_states)[0] == (
        "tasks.completed_at DESC NULLS LAST"
    )


@pytest.mark.unit
def test_recently_completed_defaults_to_descending() -> None:
    """"Recently" already means newest first, so no direction must not mean ASC."""
    assert _rendered("recently_completed", task_states=["ready"])[0].endswith("DESC NULLS LAST")


@pytest.mark.unit
def test_recently_completed_honors_explicit_ascending() -> None:
    assert _rendered("recently_completed:asc", task_states=["ready"])[0] == (
        "tasks.completed_at ASC NULLS LAST"
    )


@pytest.mark.unit
@pytest.mark.parametrize("order_by", ["recently_completed", "recently_completed:asc"])
def test_recently_completed_always_sorts_nulls_last(order_by) -> None:
    """Postgres defaults DESC to NULLS FIRST, which would put every never-completed task at
    the top of "most recently completed" — a total inversion of the feature."""
    assert "NULLS LAST" in _rendered(order_by, task_states=["ready"])[0]


@pytest.mark.unit
def test_recently_completed_composes_with_a_legacy_key() -> None:
    assert _rendered("created_at:desc,recently_completed", task_states=["ready"]) == [
        "tasks.created_at DESC",
        "tasks.completed_at DESC NULLS LAST",
        "tasks.client_id ASC",
    ]


# --- last_interacted ----------------------------------------------------------------------


@pytest.mark.unit
def test_last_interacted_aggregates_step_state_records() -> None:
    rendered = _rendered_in_statement("last_interacted")
    assert "max(step_state_records.entered_at)" in rendered
    assert "task_steps.task_id = tasks.client_id" in rendered


@pytest.mark.unit
def test_last_interacted_excludes_the_pending_creation_record() -> None:
    """Every step gets a PENDING record when it is created; counting it would date every
    untouched step to its creation and make the sort a synonym for created_at."""
    assert "step_state_records.state != 'pending'" in _rendered_in_statement("last_interacted")


@pytest.mark.unit
def test_last_interacted_excludes_records_of_removed_steps() -> None:
    """Step state records are not soft-deleted with their step, so the step's own flag is
    what has to exclude them."""
    assert "task_steps.is_deleted IS false" in _rendered_in_statement("last_interacted")


@pytest.mark.unit
def test_last_interacted_is_scoped_to_the_requested_working_sections() -> None:
    rendered = _rendered_in_statement("last_interacted", working_section_ids=["wsec_a", "wsec_b"])
    assert "task_steps.working_section_id IN ('wsec_a', 'wsec_b')" in rendered


@pytest.mark.unit
def test_last_interacted_is_unscoped_without_working_section_ids() -> None:
    assert "working_section_id" not in _rendered_in_statement("last_interacted")


@pytest.mark.unit
def test_last_interacted_is_scoped_to_the_workspace() -> None:
    rendered = _rendered_in_statement("last_interacted")
    assert f"step_state_records.workspace_id = '{WORKSPACE_ID}'" in rendered
    assert f"task_steps.workspace_id = '{WORKSPACE_ID}'" in rendered


@pytest.mark.unit
def test_last_interacted_correlates_instead_of_cross_joining_tasks() -> None:
    """A subquery that carries `tasks` in its own FROM is a cartesian product, not a
    per-row aggregate."""
    rendered = _rendered_in_statement("last_interacted")
    start = rendered.index("FROM step_state_records")
    subquery_from = rendered[start : rendered.index("WHERE", start)]
    assert "JOIN task_steps" in subquery_from
    assert "tasks" not in subquery_from.replace("task_steps", "")


@pytest.mark.unit
def test_last_interacted_defaults_to_descending_nulls_last() -> None:
    clause = _rendered("last_interacted")[0]
    assert clause.endswith("DESC NULLS LAST")


@pytest.mark.unit
def test_last_interacted_honors_explicit_ascending() -> None:
    assert _rendered("last_interacted:asc")[0].endswith("ASC NULLS LAST")


@pytest.mark.unit
def test_last_interacted_needs_no_state_filter() -> None:
    """Unlike recently_completed, this key is answerable for any task."""
    assert _rendered("last_interacted")[0].endswith("DESC NULLS LAST")


@pytest.mark.unit
def test_workspace_id_is_required() -> None:
    """A defaulted workspace_id would compile to `workspace_id IS NULL`, tie every row and
    return a silently wrong 200."""
    with pytest.raises(TypeError):
        _build_order_by("last_interacted")
