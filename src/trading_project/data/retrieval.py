from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

import pandas as pd


def _fetch_dataframe(conn: Any, sql: str, params: tuple[Any, ...]) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        columns = [description.name for description in cur.description]
    return pd.DataFrame(rows, columns=columns)


def _price_where_clause(
    tickers: Iterable[str] | None,
    start_date: dt.date | str | None,
    end_date: dt.date | str | None,
) -> tuple[str, list[Any]]:
    where = ["dv.name = %s"]
    params: list[Any] = []
    if tickers:
        where.append("sym.ticker = ANY(%s)")
        params.append([ticker.upper() for ticker in tickers])
    if start_date:
        where.append("dp.price_date >= %s")
        params.append(start_date)
    if end_date:
        where.append("dp.price_date <= %s")
        params.append(end_date)
    return " AND ".join(where), params


def get_adjusted_close(
    conn: Any,
    vendor_name: str = "yfinance",
    tickers: Iterable[str] | None = None,
    start_date: dt.date | str | None = None,
    end_date: dt.date | str | None = None,
) -> pd.DataFrame:
    where, params = _price_where_clause(tickers, start_date, end_date)
    sql = f"""
        SELECT dp.price_date, sym.ticker, dp.adj_close_price
        FROM daily_price AS dp
        JOIN symbol AS sym ON sym.id = dp.symbol_id
        JOIN data_vendor AS dv ON dv.id = dp.data_vendor_id
        WHERE {where}
        ORDER BY dp.price_date ASC, sym.ticker ASC;
    """
    frame = _fetch_dataframe(conn, sql, (vendor_name, *params))
    if not frame.empty:
        frame["price_date"] = pd.to_datetime(frame["price_date"])
        frame["adj_close_price"] = pd.to_numeric(frame["adj_close_price"])
    return frame


def get_adjusted_close_matrix(
    conn: Any,
    vendor_name: str = "yfinance",
    tickers: Iterable[str] | None = None,
    start_date: dt.date | str | None = None,
    end_date: dt.date | str | None = None,
) -> pd.DataFrame:
    frame = get_adjusted_close(conn, vendor_name, tickers, start_date, end_date)
    if frame.empty:
        return pd.DataFrame()
    return frame.pivot(index="price_date", columns="ticker", values="adj_close_price").sort_index()


def get_ohlcv(
    conn: Any,
    vendor_name: str = "yfinance",
    tickers: Iterable[str] | None = None,
    start_date: dt.date | str | None = None,
    end_date: dt.date | str | None = None,
) -> pd.DataFrame:
    where, params = _price_where_clause(tickers, start_date, end_date)
    sql = f"""
        SELECT
            dp.price_date,
            sym.ticker,
            dp.open_price,
            dp.high_price,
            dp.low_price,
            dp.close_price,
            dp.adj_close_price,
            dp.volume
        FROM daily_price AS dp
        JOIN symbol AS sym ON sym.id = dp.symbol_id
        JOIN data_vendor AS dv ON dv.id = dp.data_vendor_id
        WHERE {where}
        ORDER BY dp.price_date ASC, sym.ticker ASC;
    """
    frame = _fetch_dataframe(conn, sql, (vendor_name, *params))
    if not frame.empty:
        frame["price_date"] = pd.to_datetime(frame["price_date"])
        for column in ["open_price", "high_price", "low_price", "close_price", "adj_close_price", "volume"]:
            frame[column] = pd.to_numeric(frame[column])
    return frame
