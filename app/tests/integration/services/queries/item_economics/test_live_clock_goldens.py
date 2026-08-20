"""Pre-change payload goldens for the live-clock rollout.

These fixtures deliberately contain no COMPLETED steps and every step has an open
PENDING record.  That keeps the typicals block time-invariant: its completed-step
sample count remains zero and its typical worker seconds remain ``None`` at any
future run date.  The frozen task also has zero post-freeze drift, so its settled
figures are value-identical before and after phase 3 changes the frozen-percent
source; a drift fixture would not survive that later change.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.item_economics.serializers import serialize_task_budget_status
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_task_budget_allocations import (
    get_task_budget_allocations,
)
from beyo_manager.services.queries.item_economics.get_task_budget_status import get_task_budget_status
from beyo_manager.services.queries.item_economics.get_task_budget_status_worker import (
    get_task_budget_status_worker,
)
from beyo_manager.services.queries.item_economics.get_task_production_time import get_task_production_time


GOLDEN_DIR = Path(__file__).with_name("goldens")
FIXTURE_NOW = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
FIXTURE_ENTERED_AT = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
FROZEN_COMPUTED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _ctx(db_session, workspace_id: str, task_id: str, role_name: str) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr_live_clock_golden", "role_name": role_name},
        incoming_data={"task_client_id": task_id},
        query_params={},
        session=db_session,
    )


async def _seed_golden_fixture(db_session) -> dict[str, str]:
    workspace = Workspace(client_id="ws_live_clock_golden", name="Live clock golden workspace")
    user = User(
        client_id="usr_live_clock_golden",
        username="live_clock_golden",
        email="live_clock_golden@example.test",
        password="secret",
    )
    section = WorkingSection(
        client_id="wsec_live_clock_golden",
        workspace_id=workspace.client_id,
        name="Golden section",
        order_list=1,
    )
    idle_task = Task(
        client_id="tsk_live_clock_golden_idle",
        workspace_id=workspace.client_id,
        task_scalar_id=901,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user.client_id,
    )
    frozen_task = Task(
        client_id="tsk_live_clock_golden_frozen",
        workspace_id=workspace.client_id,
        task_scalar_id=902,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user.client_id,
    )
    idle_item = Item(
        client_id="itm_live_clock_golden_idle",
        workspace_id=workspace.client_id,
        item_major_category_snapshot="wood",
        created_by_id=user.client_id,
    )
    frozen_item = Item(
        client_id="itm_live_clock_golden_frozen",
        workspace_id=workspace.client_id,
        item_major_category_snapshot="wood",
        created_by_id=user.client_id,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add_all([section, idle_task, frozen_task, idle_item, frozen_item])
    await db_session.flush()

    group = ProductionCostGroup(
        client_id="pcg_live_clock_golden",
        workspace_id=workspace.client_id,
        name="Golden group",
        major_category="wood",
        created_by_id=user.client_id,
    )
    basis = ProductionCostBasisVersion(
        client_id="pcbv_live_clock_golden",
        workspace_id=workspace.client_id,
        production_cost_group_id=group.client_id,
        fixed_monthly_cost_minor=1,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("1.00"),
        planning_utilization_percent=Decimal("1.00"),
        cost_per_worker_minute_minor=Decimal("0.0001"),
        created_by_id=user.client_id,
    )
    model = CostModelVersion(
        client_id="cmv_live_clock_golden",
        workspace_id=workspace.client_id,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
    )
    db_session.add(group)
    await db_session.flush()
    db_session.add_all([basis, model])
    await db_session.flush()

    evaluations = [
        ItemCostEvaluation(
            client_id="ice_live_clock_golden_idle",
            workspace_id=workspace.client_id,
            task_id=idle_task.client_id,
            item_id=idle_item.client_id,
            kind=ItemCostEvaluationKindEnum.COMMITTED,
            task_type_snapshot=TaskTypeEnum.INTERNAL,
            expected_sale_price_minor=0,
            currency=ItemCurrencyEnum.SWEDISH_KRONA,
            cost_model_version_id=model.client_id,
            production_cost_group_id=group.client_id,
            production_cost_basis_version_id=basis.client_id,
            monthly_paid_hours_snapshot=Decimal("1.00"),
            planning_utilization_percent_snapshot=Decimal("1.00"),
            fixed_monthly_cost_minor_snapshot=1,
            cost_per_worker_minute_minor_snapshot=Decimal("0.0001"),
            production_budget_minor=0,
            allowed_worker_minutes=Decimal("100.00"),
            calculation_version=1,
            committed_at=FROZEN_COMPUTED_AT,
            created_at=FROZEN_COMPUTED_AT,
            created_by_id=user.client_id,
        ),
        ItemCostEvaluation(
            client_id="ice_live_clock_golden_frozen",
            workspace_id=workspace.client_id,
            task_id=frozen_task.client_id,
            item_id=frozen_item.client_id,
            kind=ItemCostEvaluationKindEnum.COMMITTED,
            task_type_snapshot=TaskTypeEnum.INTERNAL,
            expected_sale_price_minor=0,
            currency=ItemCurrencyEnum.SWEDISH_KRONA,
            cost_model_version_id=model.client_id,
            production_cost_group_id=group.client_id,
            production_cost_basis_version_id=basis.client_id,
            monthly_paid_hours_snapshot=Decimal("1.00"),
            planning_utilization_percent_snapshot=Decimal("1.00"),
            fixed_monthly_cost_minor_snapshot=1,
            cost_per_worker_minute_minor_snapshot=Decimal("0.0001"),
            production_budget_minor=0,
            allowed_worker_minutes=Decimal("100.00"),
            calculation_version=1,
            committed_at=FROZEN_COMPUTED_AT,
            created_at=FROZEN_COMPUTED_AT,
            created_by_id=user.client_id,
        ),
    ]
    db_session.add_all(evaluations)
    db_session.add_all([
        TaskItem(
            client_id="tim_live_clock_golden_idle",
            workspace_id=workspace.client_id,
            task_id=idle_task.client_id,
            item_id=idle_item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=user.client_id,
        ),
        TaskItem(
            client_id="tim_live_clock_golden_frozen",
            workspace_id=workspace.client_id,
            task_id=frozen_task.client_id,
            item_id=frozen_item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=user.client_id,
        ),
    ])
    await db_session.flush()

    steps = [
        TaskStep(
            client_id="tsp_live_clock_golden_idle",
            workspace_id=workspace.client_id,
            task_id=idle_task.client_id,
            working_section_id=section.client_id,
            state=TaskStepStateEnum.PENDING,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            sequence_order=1,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=600,
            working_section_name_snapshot="Golden section",
            created_at=FIXTURE_ENTERED_AT,
            created_by_id=user.client_id,
        ),
        TaskStep(
            client_id="tsp_live_clock_golden_frozen",
            workspace_id=workspace.client_id,
            task_id=frozen_task.client_id,
            working_section_id=section.client_id,
            state=TaskStepStateEnum.PENDING,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            sequence_order=1,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=900,
            working_section_name_snapshot="Golden section",
            created_at=FIXTURE_ENTERED_AT,
            created_by_id=user.client_id,
        ),
    ]
    db_session.add_all(steps)
    await db_session.flush()
    records = [
        StepStateRecord(
            client_id="ssr_live_clock_golden_idle",
            workspace_id=workspace.client_id,
            step_id=steps[0].client_id,
            state=TaskStepStateEnum.PENDING,
            entered_at=FIXTURE_ENTERED_AT,
            exited_at=None,
            created_by_id=user.client_id,
        ),
        StepStateRecord(
            client_id="ssr_live_clock_golden_frozen",
            workspace_id=workspace.client_id,
            step_id=steps[1].client_id,
            state=TaskStepStateEnum.PENDING,
            entered_at=FIXTURE_ENTERED_AT,
            exited_at=None,
            created_by_id=user.client_id,
        ),
    ]
    db_session.add_all(records)
    await db_session.flush()
    steps[0].latest_state_record_id = records[0].client_id
    steps[1].latest_state_record_id = records[1].client_id
    db_session.add(
        ItemCostResult(
            client_id="icr_live_clock_golden_frozen",
            workspace_id=workspace.client_id,
            task_id=frozen_task.client_id,
            item_id=frozen_item.client_id,
            evaluation_id=evaluations[1].client_id,
            actual_worker_seconds=900,
            actual_worker_minutes=Decimal("15.00"),
            consumed_cost_minor=1,
            variance_worker_minutes=Decimal("85.00"),
            variance_cost_minor=2,
            task_closed_at=None,
            task_state_snapshot=TaskStateEnum.ASSIGNED,
            calculation_version=1,
            computed_at=FROZEN_COMPUTED_AT,
            created_at=FROZEN_COMPUTED_AT,
        )
    )
    await db_session.flush()
    return {
        "idle_no_result": idle_task.client_id,
        "frozen_no_drift": frozen_task.client_id,
        "workspace_id": workspace.client_id,
    }


async def _payloads(db_session, fixture: dict[str, str]) -> dict[str, dict]:
    workspace_id = fixture["workspace_id"]
    production_time = {}
    budget_status = {}
    budget_allocations = {}
    for key in ("idle_no_result", "frozen_no_drift"):
        task_id = fixture[key]
        production_time[key] = await get_task_production_time(
            _ctx(db_session, workspace_id, task_id, "manager")
        )
        manager = await get_task_budget_status(_ctx(db_session, workspace_id, task_id, "manager"))
        worker = await get_task_budget_status_worker(_ctx(db_session, workspace_id, task_id, "worker"))
        budget_status[key] = {
            "manager": serialize_task_budget_status(manager, include_monetary=True),
            "worker": serialize_task_budget_status(worker, include_monetary=False),
        }
        budget_allocations[key] = await get_task_budget_allocations(
            ServiceContext(
                identity={"workspace_id": workspace_id, "user_id": "usr_live_clock_golden", "role_name": "worker"},
                incoming_data={},
                query_params={"task_ids": [task_id]},
                session=db_session,
            )
        )
    return {
        "production_time": production_time,
        "budget_status": budget_status,
        "budget_allocations": budget_allocations,
    }


@pytest.mark.integration
async def test_prechange_payloads_match_byte_golden_files(db_session):
    fixture = await _seed_golden_fixture(db_session)
    payloads = await _payloads(db_session, fixture)
    for name, payload in payloads.items():
        actual = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        expected = (GOLDEN_DIR / f"golden_{name}.json").read_text().strip()
        assert actual == expected
