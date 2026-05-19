from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DailyPriceRow:
    price_date: dt.date
    open_price: Decimal | None
    high_price: Decimal | None
    low_price: Decimal | None
    close_price: Decimal | None
    adj_close_price: Decimal | None
    volume: int | None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return Decimal(str(round(numeric, 6)))


def _int_or_none(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return int(numeric)


def _flatten_single_ticker_columns(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if not isinstance(frame.columns, pd.MultiIndex):
        return frame
    if ticker in frame.columns.get_level_values(-1):
        return frame.xs(ticker, axis=1, level=-1)
    if ticker in frame.columns.get_level_values(0):
        return frame.xs(ticker, axis=1, level=0)
    return frame.droplevel(-1, axis=1)


def canonicalize_price_frame(ticker: str, frame: pd.DataFrame) -> list[DailyPriceRow]:
    if frame.empty:
        return []

    normalized = _flatten_single_ticker_columns(frame.copy(), ticker)
    normalized = normalized.rename(columns={column: str(column).strip() for column in normalized.columns})
    required = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    missing = [column for column in required if column not in normalized.columns]
    if missing:
        raise ValueError(f"{ticker} yfinance data is missing columns: {missing}")

    rows: list[DailyPriceRow] = []
    for index, row in normalized.iterrows():
        if row[required].isna().all():
            continue
        timestamp = pd.Timestamp(index)
        rows.append(
            DailyPriceRow(
                price_date=timestamp.date(),
                open_price=_decimal_or_none(row["Open"]),
                high_price=_decimal_or_none(row["High"]),
                low_price=_decimal_or_none(row["Low"]),
                close_price=_decimal_or_none(row["Close"]),
                adj_close_price=_decimal_or_none(row["Adj Close"]),
                volume=_int_or_none(row["Volume"]),
            )
        )
    return rows


def fetch_daily_prices(
    ticker: str,
    start: dt.date | str | None = None,
    end: dt.date | str | None = None,
) -> list[DailyPriceRow]:
    try:
        import yfinance as yf
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "yfinance is required for price downloads. Install dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    frame = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="column",
        threads=False,
    )
    return canonicalize_price_frame(ticker, frame)
