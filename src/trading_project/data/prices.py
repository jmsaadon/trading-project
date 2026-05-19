from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

from trading_project.data.db import jsonb_param
from trading_project.data.yfinance_client import DailyPriceRow


def get_vendor_id(conn: Any, vendor_name: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM data_vendor WHERE name = %s;", (vendor_name,))
        row = cur.fetchone()
    if row is None:
        raise ValueError(f"Unknown data vendor: {vendor_name}")
    return int(row["id"])


def get_active_symbols(conn: Any, tickers: Iterable[str] | None = None) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ["is_active = TRUE"]
    if tickers:
        where.append("ticker = ANY(%s)")
        params.append([ticker.upper() for ticker in tickers])
    sql = f"""
        SELECT id, ticker
        FROM symbol
        WHERE {' AND '.join(where)}
        ORDER BY ticker ASC;
    """
    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
    return list(rows)


def get_latest_price_date(conn: Any, vendor_id: int, symbol_id: int) -> dt.date | None:
    sql = """
        SELECT MAX(price_date) AS latest_price_date
        FROM daily_price
        WHERE data_vendor_id = %s AND symbol_id = %s;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (vendor_id, symbol_id))
        row = cur.fetchone()
    return row["latest_price_date"] if row else None


def price_upsert_records(
    vendor_id: int,
    symbol_id: int,
    rows: Iterable[DailyPriceRow],
) -> list[tuple[Any, ...]]:
    return [
        (
            vendor_id,
            symbol_id,
            row.price_date,
            row.open_price,
            row.high_price,
            row.low_price,
            row.close_price,
            row.adj_close_price,
            row.volume,
        )
        for row in rows
    ]


def upsert_daily_prices(conn: Any, vendor_id: int, symbol_id: int, rows: list[DailyPriceRow]) -> int:
    records = price_upsert_records(vendor_id, symbol_id, rows)
    if not records:
        return 0
    sql = """
        INSERT INTO daily_price (
            data_vendor_id, symbol_id, price_date,
            open_price, high_price, low_price, close_price, adj_close_price, volume
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (data_vendor_id, symbol_id, price_date) DO UPDATE SET
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            adj_close_price = EXCLUDED.adj_close_price,
            volume = EXCLUDED.volume,
            updated_at = NOW();
    """
    with conn.cursor() as cur:
        cur.executemany(sql, records)
    conn.commit()
    return len(records)


def start_ingestion_run(
    conn: Any,
    command: str,
    vendor_id: int | None,
    symbols_requested: int = 0,
    metadata: dict[str, Any] | None = None,
) -> int:
    sql = """
        INSERT INTO ingestion_run (command, data_vendor_id, symbols_requested, metadata)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (command, vendor_id, symbols_requested, jsonb_param(metadata)))
        row = cur.fetchone()
    conn.commit()
    return int(row["id"])


def finish_ingestion_run(
    conn: Any,
    run_id: int,
    status: str,
    records_requested: int = 0,
    records_inserted: int = 0,
    records_updated: int = 0,
    error_message: str | None = None,
) -> None:
    sql = """
        UPDATE ingestion_run
        SET
            status = %s,
            records_requested = %s,
            records_inserted = %s,
            records_updated = %s,
            error_message = %s,
            finished_at = NOW()
        WHERE id = %s;
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                status,
                records_requested,
                records_inserted,
                records_updated,
                error_message,
                run_id,
            ),
        )
    conn.commit()
