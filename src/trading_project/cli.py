from __future__ import annotations

import argparse
import datetime as dt
import sys
from typing import Iterable

from trading_project.config import DEFAULT_SETTINGS_PATH, load_config
from trading_project.data.db import connect, execute_sql_file
from trading_project.data.prices import (
    finish_ingestion_run,
    get_active_symbols,
    get_latest_price_date,
    get_vendor_id,
    start_ingestion_run,
    upsert_daily_prices,
)
from trading_project.data.quality import run_quality_checks
from trading_project.data.seed import load_symbols, seed_exchanges, seed_vendor
from trading_project.data.universe import load_universe
from trading_project.data.yfinance_client import fetch_daily_prices


def _parse_tickers(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [ticker.strip().upper() for ticker in raw.split(",") if ticker.strip()]


def _connect_from_args(args: argparse.Namespace):
    config = load_config(args.config)
    return config, connect(config.database_url)


def command_init_db(args: argparse.Namespace) -> int:
    config, conn = _connect_from_args(args)
    universe = load_universe(config.data.universe_path)
    with conn:
        execute_sql_file(conn)
        seed_exchanges(conn, universe.exchanges)
        seed_vendor(conn, config.data_vendor)
    print("Initialized database schema and seeded static exchange/vendor rows.")
    return 0


def command_load_universe(args: argparse.Namespace) -> int:
    config, conn = _connect_from_args(args)
    universe = load_universe(config.data.universe_path)
    with conn:
        seed_exchanges(conn, universe.exchanges)
        seed_vendor(conn, config.data_vendor)
        load_symbols(conn, universe.symbols)
    print(f"Loaded {len(universe.symbols)} ETF symbols.")
    return 0


def _load_prices_for_symbols(
    conn,
    command: str,
    vendor_name: str,
    symbols: Iterable[dict],
    start: dt.date | str | None,
    incremental: bool,
) -> int:
    vendor_id = get_vendor_id(conn, vendor_name)
    symbol_list = list(symbols)
    run_id = start_ingestion_run(
        conn,
        command=command,
        vendor_id=vendor_id,
        symbols_requested=len(symbol_list),
        metadata={"incremental": incremental, "start": str(start) if start else None},
    )

    records = 0
    try:
        for symbol in symbol_list:
            symbol_start = start
            if incremental:
                latest = get_latest_price_date(conn, vendor_id, symbol["id"])
                symbol_start = latest + dt.timedelta(days=1) if latest else start
            end = dt.date.today() + dt.timedelta(days=1)
            rows = fetch_daily_prices(symbol["ticker"], start=symbol_start, end=end)
            records += upsert_daily_prices(conn, vendor_id, symbol["id"], rows)
            print(f"{symbol['ticker']}: upserted {len(rows)} rows")
        finish_ingestion_run(
            conn,
            run_id,
            status="success",
            records_requested=records,
            records_inserted=records,
        )
    except Exception as exc:
        finish_ingestion_run(conn, run_id, status="failed", error_message=str(exc))
        raise

    print(f"{command}: upserted {records} rows across {len(symbol_list)} symbols.")
    return records


def command_backfill_prices(args: argparse.Namespace) -> int:
    config, conn = _connect_from_args(args)
    tickers = _parse_tickers(args.tickers)
    start = args.start or config.data.default_backfill_start
    with conn:
        symbols = get_active_symbols(conn, tickers)
        _load_prices_for_symbols(
            conn,
            command="backfill-prices",
            vendor_name=config.data_vendor.name,
            symbols=symbols,
            start=start,
            incremental=False,
        )
    return 0


def command_update_prices(args: argparse.Namespace) -> int:
    config, conn = _connect_from_args(args)
    tickers = _parse_tickers(args.tickers)
    with conn:
        symbols = get_active_symbols(conn, tickers)
        _load_prices_for_symbols(
            conn,
            command="update-prices",
            vendor_name=config.data_vendor.name,
            symbols=symbols,
            start=config.data.default_backfill_start,
            incremental=True,
        )
    return 0


def command_check_data_quality(args: argparse.Namespace) -> int:
    config, conn = _connect_from_args(args)
    with conn:
        vendor_id = get_vendor_id(conn, config.data_vendor.name)
        run_id = start_ingestion_run(
            conn,
            command="check-data-quality",
            vendor_id=vendor_id,
            symbols_requested=0,
            metadata={"stale_days": args.stale_days or config.data.stale_days},
        )
        try:
            issue_count = run_quality_checks(
                conn,
                vendor_id=vendor_id,
                ingestion_run_id=run_id,
                stale_days=args.stale_days or config.data.stale_days,
            )
            finish_ingestion_run(conn, run_id, status="success", records_inserted=issue_count)
        except Exception as exc:
            finish_ingestion_run(conn, run_id, status="failed", error_message=str(exc))
            raise
    print(f"Logged {issue_count} open data quality issues.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ETF data collection and storage commands.")
    parser.add_argument("--config", default=str(DEFAULT_SETTINGS_PATH), help="Path to settings YAML.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db = subparsers.add_parser("init-db", help="Create schema and seed static rows.")
    init_db.set_defaults(func=command_init_db)

    load_universe_parser = subparsers.add_parser("load-universe", help="Load ETF symbols.")
    load_universe_parser.set_defaults(func=command_load_universe)

    backfill = subparsers.add_parser("backfill-prices", help="Backfill daily ETF prices.")
    backfill.add_argument("--tickers", help="Comma-separated ticker subset.")
    backfill.add_argument("--start", help="Backfill start date, YYYY-MM-DD.")
    backfill.set_defaults(func=command_backfill_prices)

    update = subparsers.add_parser("update-prices", help="Update missing daily ETF prices.")
    update.add_argument("--tickers", help="Comma-separated ticker subset.")
    update.set_defaults(func=command_update_prices)

    quality = subparsers.add_parser("check-data-quality", help="Run practical data checks.")
    quality.add_argument("--stale-days", type=int, help="Days before latest data is stale.")
    quality.set_defaults(func=command_check_data_quality)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
