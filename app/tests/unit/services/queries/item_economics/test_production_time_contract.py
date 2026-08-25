from pathlib import Path

from beyo_manager.domain.item_economics import budget_division


def test_c19_division_has_one_allocator_and_services_only_consume_it():
    root = Path(__file__).resolve().parents[5]
    services = root / "beyo_manager" / "services" / "queries" / "item_economics"
    importing = {
        path.stem
        for path in services.glob("*.py")
        if "divide_production_budget" in path.read_text()
    }
    assert importing == {
        "get_task_budget_allocations",
        "get_task_budget_signals",
        "get_task_production_time",
    }
    for name in importing:
        source = (services / f"{name}.py").read_text()
        assert "Fraction" not in source
        assert "ROUND_HALF_EVEN" not in source
        assert "largest" not in source
        assert "//" not in source
    assert [name for name in budget_division.__all__ if "divide" in name] == ["divide_production_budget"]
