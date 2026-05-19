import datetime as dt
from decimal import Decimal

from trading_project.data.prices import price_upsert_records
from trading_project.data.yfinance_client import DailyPriceRow


def test_price_upsert_records_preserve_vendor_symbol_and_precision():
    rows = [
        DailyPriceRow(
            price_date=dt.date(2024, 1, 2),
            open_price=Decimal("1.1"),
            high_price=Decimal("1.2"),
            low_price=Decimal("1.0"),
            close_price=Decimal("1.15"),
            adj_close_price=Decimal("1.14"),
            volume=1000,
        )
    ]

    records = price_upsert_records(vendor_id=7, symbol_id=42, rows=rows)

    assert records == [
        (
            7,
            42,
            dt.date(2024, 1, 2),
            Decimal("1.1"),
            Decimal("1.2"),
            Decimal("1.0"),
            Decimal("1.15"),
            Decimal("1.14"),
            1000,
        )
    ]
