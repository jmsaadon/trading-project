from decimal import Decimal

import pandas as pd

from trading_project.data.yfinance_client import canonicalize_price_frame


def test_canonicalize_price_frame_maps_ohlcv_and_adjusted_close():
    frame = pd.DataFrame(
        {
            "Open": [10.1234567],
            "High": [10.5],
            "Low": [9.75],
            "Close": [10.25],
            "Adj Close": [10.01],
            "Volume": [123456],
        },
        index=pd.to_datetime(["2024-01-02"]),
    )

    rows = canonicalize_price_frame("SPY", frame)

    assert len(rows) == 1
    assert rows[0].price_date.isoformat() == "2024-01-02"
    assert rows[0].open_price == Decimal("10.123457")
    assert rows[0].adj_close_price == Decimal("10.01")
    assert rows[0].volume == 123456


def test_canonicalize_price_frame_supports_single_ticker_multiindex():
    frame = pd.DataFrame(
        {
            ("Open", "SPY"): [10.0],
            ("High", "SPY"): [11.0],
            ("Low", "SPY"): [9.0],
            ("Close", "SPY"): [10.5],
            ("Adj Close", "SPY"): [10.4],
            ("Volume", "SPY"): [100],
        },
        index=pd.to_datetime(["2024-01-02"]),
    )

    rows = canonicalize_price_frame("SPY", frame)

    assert len(rows) == 1
    assert rows[0].high_price == Decimal("11.0")
