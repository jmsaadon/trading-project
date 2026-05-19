from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd

from trading_project.data.db import jsonb_param


@dataclass(frozen=True)
class MissingDateGap:
    symbol_id: int
    ticker: str
    start_date: dt.date
    end_date: dt.date
    missing_dates: tuple[dt.date, ...]


def find_missing_business_day_gaps(
    symbol_id: int,
    ticker: str,
    dates: Iterable[dt.date],
    min_missing_days: int = 2,
) -> list[MissingDateGap]:
    ordered = sorted(set(dates))
    gaps: list[MissingDateGap] = []
    for previous, current in zip(ordered, ordered[1:]):
        expected = pd.bdate_range(previous, current).date
        missing = tuple(day for day in expected[1:-1] if day.weekday() < 5)
        if len(missing) >= min_missing_days:
            gaps.append(
                MissingDateGap(
                    symbol_id=symbol_id,
                    ticker=ticker,
                    start_date=previous,
                    end_date=current,
                    missing_dates=missing,
                )
            )
    return gaps


def _insert_issue(
    conn: Any,
    issue_type: str,
    severity: str,
    message: str,
    ingestion_run_id: int | None = None,
    data_vendor_id: int | None = None,
    symbol_id: int | None = None,
    price_date: dt.date | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    sql = """
        INSERT INTO data_quality_issue (
            ingestion_run_id, data_vendor_id, symbol_id, price_date,
            issue_type, severity, message, details
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                ingestion_run_id,
                data_vendor_id,
                symbol_id,
                price_date,
                issue_type,
                severity,
                message,
                jsonb_param(details),
            ),
        )


def clear_open_quality_issues(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE data_quality_issue
            SET resolved_at = NOW()
            WHERE resolved_at IS NULL;
            """
        )
    conn.commit()


def run_quality_checks(
    conn: Any,
    vendor_id: int,
    ingestion_run_id: int | None = None,
    stale_days: int = 7,
) -> int:
    clear_open_quality_issues(conn)
    issue_count = 0

    checks = [
        (
            "duplicate_daily_price",
            "error",
            """
            SELECT data_vendor_id, symbol_id, price_date, COUNT(*) AS row_count
            FROM daily_price
            WHERE data_vendor_id = %s
            GROUP BY data_vendor_id, symbol_id, price_date
            HAVING COUNT(*) > 1;
            """,
            lambda row: (
                row["symbol_id"],
                row["price_date"],
                f"Duplicate daily price rows found for symbol_id={row['symbol_id']} on {row['price_date']}.",
                {"row_count": row["row_count"]},
            ),
        ),
        (
            "bad_ohlc",
            "error",
            """
            SELECT symbol_id, price_date, open_price, high_price, low_price, close_price
            FROM daily_price
            WHERE data_vendor_id = %s
              AND (
                high_price < low_price
                OR open_price > high_price OR open_price < low_price
                OR close_price > high_price OR close_price < low_price
              );
            """,
            lambda row: (
                row["symbol_id"],
                row["price_date"],
                f"Bad OHLC bounds found for symbol_id={row['symbol_id']} on {row['price_date']}.",
                {
                    "open_price": str(row["open_price"]),
                    "high_price": str(row["high_price"]),
                    "low_price": str(row["low_price"]),
                    "close_price": str(row["close_price"]),
                },
            ),
        ),
        (
            "null_adjusted_close",
            "error",
            """
            SELECT symbol_id, price_date
            FROM daily_price
            WHERE data_vendor_id = %s
              AND adj_close_price IS NULL;
            """,
            lambda row: (
                row["symbol_id"],
                row["price_date"],
                f"Null adjusted close found for symbol_id={row['symbol_id']} on {row['price_date']}.",
                {},
            ),
        ),
        (
            "unexpected_volume",
            "warning",
            """
            SELECT symbol_id, price_date, volume
            FROM daily_price
            WHERE data_vendor_id = %s
              AND (volume IS NULL OR volume <= 0);
            """,
            lambda row: (
                row["symbol_id"],
                row["price_date"],
                f"Unexpected volume found for symbol_id={row['symbol_id']} on {row['price_date']}.",
                {"volume": row["volume"]},
            ),
        ),
    ]

    for issue_type, severity, sql, formatter in checks:
        with conn.cursor() as cur:
            cur.execute(sql, (vendor_id,))
            rows = cur.fetchall()
        for row in rows:
            symbol_id, price_date, message, details = formatter(row)
            _insert_issue(
                conn,
                issue_type=issue_type,
                severity=severity,
                message=message,
                ingestion_run_id=ingestion_run_id,
                data_vendor_id=vendor_id,
                symbol_id=symbol_id,
                price_date=price_date,
                details=details,
            )
            issue_count += 1

    stale_cutoff = dt.date.today() - dt.timedelta(days=stale_days)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sym.id AS symbol_id, sym.ticker, MAX(dp.price_date) AS latest_price_date
            FROM symbol AS sym
            LEFT JOIN daily_price AS dp
              ON dp.symbol_id = sym.id AND dp.data_vendor_id = %s
            WHERE sym.is_active = TRUE
            GROUP BY sym.id, sym.ticker
            HAVING MAX(dp.price_date) IS NULL OR MAX(dp.price_date) < %s;
            """,
            (vendor_id, stale_cutoff),
        )
        stale_rows = cur.fetchall()
    for row in stale_rows:
        message = f"Stale or missing latest price for {row['ticker']}."
        _insert_issue(
            conn,
            issue_type="stale_latest_price",
            severity="warning",
            message=message,
            ingestion_run_id=ingestion_run_id,
            data_vendor_id=vendor_id,
            symbol_id=row["symbol_id"],
            details={"latest_price_date": str(row["latest_price_date"]), "stale_cutoff": str(stale_cutoff)},
        )
        issue_count += 1

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sym.id AS symbol_id, sym.ticker, dp.price_date
            FROM symbol AS sym
            JOIN daily_price AS dp
              ON dp.symbol_id = sym.id
            WHERE dp.data_vendor_id = %s
            ORDER BY sym.ticker ASC, dp.price_date ASC;
            """,
            (vendor_id,),
        )
        date_rows = cur.fetchall()

    dates_by_symbol: dict[tuple[int, str], list[dt.date]] = {}
    for row in date_rows:
        dates_by_symbol.setdefault((row["symbol_id"], row["ticker"]), []).append(row["price_date"])

    for (symbol_id, ticker), dates in dates_by_symbol.items():
        for gap in find_missing_business_day_gaps(symbol_id, ticker, dates):
            _insert_issue(
                conn,
                issue_type="missing_business_day_gap",
                severity="warning",
                message=f"{ticker} has a multi-business-day gap from {gap.start_date} to {gap.end_date}.",
                ingestion_run_id=ingestion_run_id,
                data_vendor_id=vendor_id,
                symbol_id=symbol_id,
                price_date=gap.end_date,
                details={
                    "start_date": str(gap.start_date),
                    "end_date": str(gap.end_date),
                    "missing_dates": [str(date) for date in gap.missing_dates],
                    "calendar_note": "Uses a weekday calendar and intentionally ignores single-day gaps to avoid most market holidays.",
                },
            )
            issue_count += 1

    conn.commit()
    return issue_count
