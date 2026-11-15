"""Static guard for the inventory ledger's single choke point.

The repo has no type checker, so a forgotten ``movement=`` would only fail when that code path
runs, and a direct write to a quantity column would silently skip the ledger. This test parses
every module under ``beyo_manager`` and ``scripts`` and fails on either.
"""

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[5]
SCAN_ROOTS = [APP_ROOT / "beyo_manager", APP_ROOT / "scripts"]

MUTATIONS_MODULE = Path("beyo_manager/services/commands/upholstery/_inventory_mutations.py")
HELPERS_REQUIRING_MOVEMENT = {
    "check_and_inject_need",
    "consume_to_in_use",
    "finish_in_use",
    "add_ordered",
    "confirm_ordered_to_stock",
    "add_stored_surplus",
    "adjust_need",
    "complete_available_direct",
    "rollback_in_use_to_stored",
    "set_stored_amount",
    "cancel_requirements_in_session",
    "cancel_unfinished_item_requirements_in_session",
    "apply_upholstery_installation_side_effect",
    "_create_initial_requirement_for_item_upholstery",
    "_create_item_upholstery_in_session",
}
QUANTITY_ATTRIBUTES = {
    "current_stored_amount_meters",
    "current_amount_in_use_meters",
    "current_amount_in_need_meters",
    "current_amount_ordered_meters",
    "total_upholstery_used_meters",
    "total_upholstery_used_inventory_meters",
    "total_upholstery_used_surplus_meters",
    "total_upholstery_surplus_meters",
}
# Files allowed to construct an inventory row with initial quantities (each records
# inventory_created / the migration baseline right after).
INVENTORY_CONSTRUCTORS = {
    MUTATIONS_MODULE,
    Path("beyo_manager/services/commands/upholstery/create_upholstery.py"),
    Path("beyo_manager/services/commands/upholstery/create_upholstery_inventory.py"),
}


def _modules():
    for root in SCAN_ROOTS:
        for path in root.rglob("*.py"):
            yield path.relative_to(APP_ROOT), ast.parse(path.read_text(), filename=str(path))


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def test_every_ledger_helper_call_passes_movement():
    offenders = []
    for rel, tree in _modules():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node) in HELPERS_REQUIRING_MOVEMENT:
                if not any(kw.arg == "movement" for kw in node.keywords):
                    offenders.append(f"{rel}:{node.lineno} {_call_name(node)}()")
    assert offenders == [], "calls missing movement=:\n" + "\n".join(offenders)


def test_quantity_columns_are_assigned_only_in_the_mutation_helpers():
    offenders = []
    for rel, tree in _modules():
        if rel == MUTATIONS_MODULE:
            continue
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                targets = [node.target]
            for target in targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Attribute) and sub.attr in QUANTITY_ATTRIBUTES:
                        offenders.append(f"{rel}:{node.lineno} .{sub.attr}")
    assert offenders == [], "quantity writes outside _inventory_mutations.py:\n" + "\n".join(offenders)


def test_inventory_rows_are_constructed_only_where_creation_is_recorded():
    offenders = []
    for rel, tree in _modules():
        if rel in INVENTORY_CONSTRUCTORS:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node) == "UpholsteryInventory":
                offenders.append(f"{rel}:{node.lineno}")
    assert offenders == [], "UpholsteryInventory(...) outside allow-list:\n" + "\n".join(offenders)
