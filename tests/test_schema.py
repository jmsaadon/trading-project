from pathlib import Path


SCHEMA = Path("src/trading_project/data/schema.sql").read_text(encoding="utf-8")


def test_schema_contains_securities_master_tables():
    for table in [
        "exchange",
        "data_vendor",
        "symbol",
        "daily_price",
        "ingestion_run",
        "data_quality_issue",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in SCHEMA


def test_schema_has_idempotent_daily_price_constraint():
    assert "UNIQUE (data_vendor_id, symbol_id, price_date)" in SCHEMA
    assert "NUMERIC(19, 6)" in SCHEMA
    assert "volume BIGINT" in SCHEMA
