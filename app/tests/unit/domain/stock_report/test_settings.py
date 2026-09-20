import pytest
from beyo_manager.config import Settings


@pytest.mark.unit
def test_stock_report_settings_defaults_and_environment_aliases(monkeypatch):
    monkeypatch.setenv("MANAGER_API_KEY_TO_LOCATION_TRACKER_APP", "key")
    monkeypatch.setenv("LOCATION_TRACKER_WEBHOOK_WORKSPACE_ID", "ws_key")
    monkeypatch.setenv("STOCK_DEMAND_WEBHOOK_TIMEOUT_MS", "1234")
    settings = Settings()
    assert settings.manager_api_key_to_location_tracker_app == "key"
    assert settings.location_tracker_webhook_workspace_id == "ws_key"
    assert settings.stock_demand_webhook_timeout_ms == 1234


@pytest.mark.unit
def test_stock_demand_timeout_default_is_five_seconds():
    assert Settings.model_fields["stock_demand_webhook_timeout_ms"].default == 5000
