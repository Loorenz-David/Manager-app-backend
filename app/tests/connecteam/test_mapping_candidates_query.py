from beyo_manager.services.queries.users.get_connecteam_mapping_candidates import (
    get_connecteam_mapping_candidates,
)


def test_candidate_query_is_workspace_aware_and_returns_frozen_rows(monkeypatch):
    captured = {}

    class Result:
        def all(self):
            return [("usr_1", "Anna", "uwp_1", "ws_1", "99")]

    class Session:
        async def execute(self, statement):
            captured["statement"] = statement
            return Result()

    rows = __import__("asyncio").run(
        get_connecteam_mapping_candidates(Session(), workspace_id="ws_1")
    )

    assert rows[0].user_id == "usr_1"
    assert rows[0].connecteam_user_id == "99"
    assert "ws_1" in captured["statement"].compile().params.values()
