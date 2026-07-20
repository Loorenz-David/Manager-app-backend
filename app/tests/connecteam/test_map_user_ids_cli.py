import json

from typer.testing import CliRunner

from beyo_manager.domain.connecteam.user_mapping_report import ConnecteamUserMappingReport
from scripts.backfill import map_connecteam_user_ids as cli_module


def test_flag_validation_is_mutually_exclusive():
    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["--dry-run", "--execute"])

    assert result.exit_code == 1
    assert "mutually exclusive" in result.output


def test_report_json_is_valid():
    payload = ConnecteamUserMappingReport().to_dict()

    assert json.loads(json.dumps(payload)) == payload


def test_missing_file_exits_one_before_database(monkeypatch, tmp_path):
    called = False

    async def fail_init_db():
        nonlocal called
        called = True
        raise AssertionError("database should not initialize for a missing CSV")

    monkeypatch.setattr(cli_module, "init_db", fail_init_db)
    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["--file", str(tmp_path / "missing.csv")])

    assert result.exit_code == 1
    assert "missing.csv" in result.output
    assert called is False
