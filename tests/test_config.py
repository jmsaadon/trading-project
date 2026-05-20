from trading_project.config import DEFAULT_UNIVERSE_PATH, load_config


def test_load_config_returns_runtime_settings(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        """
database:
  url: postgresql://example:example@localhost:5432/example

data_vendor:
  name: yfinance
  website_url: https://finance.yahoo.com
  support_email:

data:
  frequency: daily
  universe_path: config/universe.yaml
  default_backfill_start: "1990-01-01"
  stale_days: 7
""",
        encoding="utf-8",
    )

    config = load_config(settings_path)

    assert config.database_url == "postgresql://example:example@localhost:5432/example"
    assert config.data_vendor.name == "yfinance"
    assert config.data.frequency == "daily"
    assert config.data.universe_path == DEFAULT_UNIVERSE_PATH
    assert config.data.default_backfill_start == "1990-01-01"
    assert config.data.stale_days == 7
